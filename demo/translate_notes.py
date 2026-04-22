# traduit les notes (IA et humaines) en anglais pour la démo, le jury était international
#   OPENROUTER_API_KEY=... python demo/translate_notes.py   puis relancer build_data.py
# ne touche à aucune étiquette, et la démo affiche que la note humaine est une traduction
import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "llm_labels" / "notes_en.jsonl"
AI = DATA / "llm_labels" / "google_gemini-2.5-flash.jsonl"
URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.5-flash"
BATCH = 25  # notes par requête
SYSTEM = ("Translate each French note about a clinical trial's primary outcomes into concise English. "
          "Keep trial-specific abbreviations, numbers and outcome names exactly. Return JSON: "
          '{"translations": [{"id": ..., "en": ...}]} with one entry per input id.')
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["translations"],
          "properties": {"translations": {"type": "array", "items": {
              "type": "object", "additionalProperties": False, "required": ["id", "en"],
              "properties": {"id": {"type": "string"}, "en": {"type": "string"}}}}}}


def jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def translate(session, batch):
    body = {"model": MODEL, "usage": {"include": True}, "provider": {"require_parameters": True},
            "response_format": {"type": "json_schema", "json_schema": {"name": "t", "strict": True, "schema": SCHEMA}},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": json.dumps([{"id": f"{n}|{k}", "fr": t} for n, k, t in batch],
                                                                ensure_ascii=False)}]}
    for _ in range(3):
        try:
            r = session.post(URL, json=body, timeout=180)
        except requests.RequestException:
            continue
        if r.status_code in (401, 402):
            sys.exit(f"OpenRouter : HTTP {r.status_code} (clé invalide ou crédit épuisé).")
        if r.status_code != 200:
            continue
        data = r.json()
        try:
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", data["choices"][0]["message"]["content"].strip())
            out = {t["id"]: t["en"] for t in json.loads(text)["translations"]}
        except (KeyError, TypeError, ValueError):
            continue
        return out, (data.get("usage") or {}).get("cost") or 0
    return {}, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cost", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("OPENROUTER_API_KEY absente.")
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {key}"

    done = {(r["nct"], r["kind"]) for r in jsonl(OUT)}
    todo = [(r["nct"], "ai", r["note"]) for r in jsonl(AI)]
    todo += [(r["nct"], "human", r["note"]) for r in jsonl(DATA / "labels.jsonl")]
    todo = [t for t in todo if (t[0], t[1]) not in done and t[2].strip()]
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"{len(todo)} notes à traduire ({len(batches)} lots)")
    lock, state = threading.Lock(), {"cost": 0.0, "n": 0}

    def work(batch):
        if state["cost"] >= args.max_cost:
            return
        out, cost = translate(session, batch)
        with lock, OUT.open("a") as f:
            state["cost"] += cost
            for n, k, _ in batch:
                if out.get(f"{n}|{k}"):
                    f.write(json.dumps({"nct": n, "kind": k, "note_en": out[f"{n}|{k}"]}, ensure_ascii=False) + "\n")
                    state["n"] += 1

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, batches))
    print(f"{state['n']} notes traduites, coût {state['cost']:.3f} $ -> {OUT.relative_to(ROOT)}"
          + (" (plafond atteint)" if state["cost"] >= args.max_cost else ""))


if __name__ == "__main__":
    main()
