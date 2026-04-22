# serveur de la démo : sert demo/app/ + une petite api json
#   python demo/server.py [--port 8000]
#   OPENROUTER_API_KEY=... python demo/server.py   # active le classement en direct
# routes : GET /api/status, GET /api/trial/<NCT>, GET /api/history/<NCT>, POST /api/classify/<NCT>
# écoute que sur 127.0.0.1, la clé ne part jamais au navigateur
import argparse
import json
import mimetypes
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
APP = HERE / "app"
CACHE = Path(os.environ.get("DEMO_CACHE", HERE / "cache" / "live.jsonl"))  # les tests en mettent un temporaire
for d in ("classify", "collect", "demo"):
    sys.path.insert(0, str(ROOT / d))
from batches import items
from build_data import meta
from build_items import build_item
from llm_classify import Skip, classify_openrouter
from run import collect_trial
from timeline import NoHistory, history
from wayback import Unavailable, write_gz

API = "https://clinicaltrials.gov/api/v2/studies/{}"
MODEL = "google/gemini-2.5-flash"  # TODO même valeur que dans llm_classify et build_data, à mettre au même endroit
NCT_RE = re.compile(r"^NCT\d{8}$")

KEY = os.environ.get("OPENROUTER_API_KEY")
live_left = int(os.environ.get("DEMO_MAX_LIVE", "30"))  # pour pas exploser le crédit pendant une présentation
lock = threading.Lock()
running = set()
its, trials, idx, live = {}, {}, {}, {}


class DemoError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def load():
    its.update(items())
    trials.update({t["nct"]: t for t in json.loads((APP / "data" / "trials.json").read_text())})
    idx.update({r["nct"]: r for r in map(json.loads, (ROOT / "data" / "index.jsonl").read_text().splitlines())})
    if CACHE.exists():
        live.update({r["nct"]: r for r in map(json.loads, filter(str.strip, CACHE.read_text().splitlines()))})


def get_trial(nct):
    if nct in trials:
        return {"source": "corpus", "trial": trials[nct], "item": its[nct]}
    if nct in live:
        return {"source": "live", "trial": live[nct]["trial"], "item": live[nct]["item"]}
    raise DemoError(404, "not_found", f"{nct} is not in the corpus and has not been classified live yet.")


def classify(nct):
    if nct in trials or nct in live:
        return get_trial(nct)
    if not KEY:
        raise DemoError(503, "no_key", "Live classification is off: start the server with OPENROUTER_API_KEY.")
    with lock:
        if nct in running:
            raise DemoError(409, "busy", f"{nct} is already being classified.")
        if live_left <= 0:
            raise DemoError(429, "budget", "Live classification limit reached for this session (DEMO_MAX_LIVE).")
        running.add(nct)
    try:
        return classify_live(nct)
    finally:
        with lock:
            running.discard(nct)


def classify_live(nct):
    # même chaîne que pour le corpus : ct.gov -> wayback -> paire -> LLM. compter 20 à 60 s
    global live_left
    r = requests.get(API.format(nct), timeout=60)
    if r.status_code == 404:
        raise DemoError(404, "unknown_trial", f"{nct} does not exist on ClinicalTrials.gov.")
    r.raise_for_status()
    cur = r.json()
    oms = cur.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    if not any(o.get("type") == "PRIMARY" for o in oms):
        raise DemoError(422, "no_results", f"{nct} has no primary outcome results posted: nothing to compare yet.")
    write_gz(ROOT / "data" / "current" / f"{nct}.json.gz", cur)
    try:
        row = collect_trial(nct)
    except Unavailable:
        raise DemoError(502, "wayback_down", "The Internet Archive (Wayback Machine) is not responding; try again later.")
    if row["status"] == "absent_wayback":
        raise DemoError(422, "no_history", f"No archived registry history for {nct}: the Wayback Machine crawl "
                        "(February 2025) did not capture it, so the registered version cannot be recovered.")
    if row["status"] != "ok":
        raise DemoError(422, "incomplete_history", f"Archived history of {nct} is incomplete ({row['status']}).")
    item = build_item(nct, row["ref_version"])
    trial = {"nct": nct, **meta(nct), "retrospective": bool(row["retrospective"]),
             "n_registered": len(item["registered"]), "n_posted": len(item["deposited"]),
             "ref_version": row["ref_version"]}
    if not item["registered"]:
        raise DemoError(422, "no_registered", f"The reference version of {nct} lists no primary outcome.")
    cost = 0
    if "label" in item:
        trial["auto"] = "identique"
    else:
        s = requests.Session()
        s.headers["Authorization"] = f"Bearer {KEY}"
        try:
            lab = classify_openrouter(s, item, MODEL, None, note_lang="en")
        except Skip as e:
            raise DemoError(502, "model_error", f"The model did not return a valid label ({e}).")
        except SystemExit:  # llm_classify fait sys.exit sur 401/402, pas top mais bon
            raise DemoError(502, "model_auth", "OpenRouter refused the request (invalid key or no credit left).")
        with lock:  # on ne décompte que les appels qui ont marché
            live_left -= 1
        cost = lab.get("cost") or 0
        trial["ai"] = {"verdict": lab["verdict"], "types": lab["types"], "gravite": lab["gravite"],
                       "note": lab["note"], "note_en": lab["note"], "model": lab["by"]}
    rec = {"nct": nct, "trial": trial, "item": item, "cost": cost, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with lock:
        live[nct] = rec
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"live: {nct} classified ({trial.get('ai', {}).get('verdict', 'identique')}, {cost:.4f} $)", flush=True)
    return {"source": "live", "trial": trial, "item": item}


def get_history(nct):
    if nct in trials:
        ref = idx[nct]["ref_version"]
    elif nct in live:
        ref = live[nct]["trial"]["ref_version"]
    else:
        raise DemoError(404, "not_found", f"{nct} is unknown here.")
    try:
        return history(nct, ref=ref)
    except NoHistory:
        raise DemoError(404, "no_history", f"No archived history for {nct}.")
    except Unavailable:
        raise DemoError(502, "wayback_down", "The Internet Archive is not responding; try again later.")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def route(self, method):
        path = self.path.split("?")[0]
        m = re.fullmatch(r"/api/(trial|history|classify)/(\w+)", path)
        try:
            if path == "/api/status" and method == "GET":
                return self.send_json(200, {"live": bool(KEY), "live_left": live_left, "model": MODEL})
            if m:
                kind, nct = m.group(1), m.group(2).upper()
                if not NCT_RE.match(nct):
                    raise DemoError(400, "bad_id", "An NCT number looks like NCT01234567.")
                if kind == "trial" and method == "GET":
                    return self.send_json(200, get_trial(nct))
                if kind == "history" and method == "GET":
                    return self.send_json(200, get_history(nct))
                if kind == "classify" and method == "POST":
                    return self.send_json(200, classify(nct))
                raise DemoError(405, "method", "Method not allowed.")
            if method == "GET":
                return self.static(path)
            raise DemoError(404, "not_found", "Not found.")
        except DemoError as e:
            self.send_json(e.status, {"error": e.code, "message": e.message})
        except requests.RequestException as e:
            self.send_json(502, {"error": "network", "message": f"Network error ({type(e).__name__})."})
        except Exception as e:  # surtout pas planter en pleine démo devant le jury
            print(f"error on {path}: {e!r}", flush=True)
            self.send_json(500, {"error": "internal", "message": "Unexpected server error (see server log)."})

    def static(self, path):
        f = (APP / (path.lstrip("/") or "index.html")).resolve()
        if not f.is_relative_to(APP) or not f.is_file():  # pas de ../../ qui sort de app/
            raise DemoError(404, "not_found", "Not found.")
        body = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(f.name)[0] or "application/octet-stream")
                         + ("; charset=utf-8" if f.suffix in (".html", ".json", ".js", ".css") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    if not (APP / "data" / "trials.json").exists():
        sys.exit("pas de demo/app/data/, lancer d'abord python demo/build_data.py")
    load()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Outcome Switch Monitor: http://127.0.0.1:{args.port}  — live classification "
          f"{'on' if KEY else 'off (no OPENROUTER_API_KEY)'}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
