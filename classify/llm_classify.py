# classement des essais par LLM (openrouter), avec GUIDELINES.md comme prompt
#   python classify/llm_classify.py --eval            # sur les 95 annotés -> accord avec les humains
#   python classify/llm_classify.py --workers 16 --max-cost 15   # tout le reste du corpus
# sortie : data/llm_labels/<modele>.jsonl (reprend où ça s'était arrêté)
import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from batches import TYPES, VERDICTS, fmt_item, items

OUT_DIR = ROOT / "data" / "llm_labels"
LABELS = ROOT / "data" / "labels.jsonl"
MODEL = "google/gemini-2.5-flash"  # meilleur compromis sur les 4 testés, cf METHODE.md
OPENROUTER = os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")  # les tests mettent un faux serveur

SYSTEM = (
    "Tu annotes des essais cliniques pour une étude de méta-recherche sur les discordances entre "
    "critères principaux enregistrés et déposés. Applique exactement les règles suivantes.\n\n"
    + (HERE / "GUIDELINES.md").read_text()
    + "\n\nFormat de l'essai : lignes « ENR: » = critères principaux enregistrés au début de l'essai, "
    "« DEP: » = critères principaux déposés avec les résultats, « SEC: » = titres des critères "
    "secondaires déposés (seulement pour repérer une rétrogradation). Chaque ligne : mesure "
    "[délai] — description (400 premiers caractères). Si le verdict n'est pas « changement », types = [] et "
    "gravite = « aucune »."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": sorted(VERDICTS)},
        "types": {"type": "array", "items": {"type": "string", "enum": sorted(TYPES)}},
        "gravite": {"type": "string", "enum": ["majeur", "mineur", "aucune"]},
        "note": {"type": "string"},
    },
    "required": ["verdict", "types", "gravite", "note"],
    "additionalProperties": False,
}


class Skip(Exception):
    pass


def label(nct, r, by, cost):
    if r["verdict"] not in VERDICTS or not set(r["types"]) <= TYPES:
        raise Skip(f"réponse hors vocabulaire : {r}")
    chg = r["verdict"] == "changement"
    return {"nct": nct, "verdict": r["verdict"], "types": r["types"] if chg else [],
            "gravite": r["gravite"] if chg and r["gravite"] != "aucune" else None,
            "note": r["note"], "by": by, "cost": cost}


def classify_openrouter(session, it, model, effort, note_lang=None):
    # note_lang="en" pour la démo (jury international), le prompt reste en français
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": fmt_item(it) + ("\n\nWrite the note in English." if note_lang == "en" else "")}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "label", "strict": True, "schema": SCHEMA}},
        "provider": {"require_parameters": True},
        "max_tokens": 4000,
        "usage": {"include": True},
    }
    if effort:
        body["reasoning"] = {"effort": effort}
    for attempt in range(3):
        try:
            r = session.post(OPENROUTER, json=body, timeout=180)
        except requests.RequestException as e:
            err = f"connexion ({type(e).__name__})"
            continue
        if r.status_code == 401:
            sys.exit("Clé OpenRouter invalide.")
        if r.status_code == 402:
            sys.exit("Crédit OpenRouter épuisé.")
        if r.status_code in (429, 500, 502, 503, 504):
            err = f"HTTP {r.status_code}"
            continue
        if r.status_code != 200:
            raise Skip(f"HTTP {r.status_code} : {r.text[:200]}")
        data = r.json()
        if "error" in data:
            err = str(data["error"])[:200]
            continue
        text = data["choices"][0]["message"].get("content") or ""
        # certains modèles entourent quand même le json de ```, malgré response_format
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        try:
            out = json.loads(text)
        except json.JSONDecodeError:
            err = "JSON invalide"
            continue
        return label(it["nct"], out, data.get("model", model), (data.get("usage") or {}).get("cost"))
    raise Skip(f"échec après 3 essais : {err}")


# TODO évaluer sur un vrai jeu de test : là c'est mesuré sur les 95 essais qui ont aussi servi
# à choisir le modèle et à préciser les règles, donc sûrement un peu optimiste
def agreement(pred):
    ref = {r["nct"]: r for r in map(json.loads, LABELS.read_text().splitlines())}
    ids = [n for n in pred if n in ref]
    if len(ids) < 2:
        return
    from sklearn.metrics import cohen_kappa_score
    print(f"Accord avec les étiquettes humaines finales (n = {len(ids)}) :")
    for name, f in (("changement oui / non", lambda r: r["verdict"] == "changement"),
                    ("verdict (4 classes)", lambda r: r["verdict"]),
                    ("changement majeur oui / non", lambda r: r["gravite"] == "majeur")):
        x, y = [f(ref[n]) for n in ids], [f(pred[n]) for n in ids]
        acc = sum(i == j for i, j in zip(x, y)) / len(ids)
        k = cohen_kappa_score(x, y) if len(set(x + y)) > 1 else float("nan")
        print(f"  {name} : {100 * acc:.0f} %, kappa {k:.2f}")
    p = lambda r: r["verdict"] == "changement"
    pos = sum(p(pred[n]) for n in ids)
    print(f"  essais « changement » : humains {sum(p(ref[n]) for n in ids)}, modèle {pos}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--effort")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-cost", type=float, help="en $")
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("OPENROUTER_API_KEY absente.")
    client = requests.Session()
    client.headers.update({"Authorization": f"Bearer {key}"})

    its = items()
    if not LABELS.exists():
        sys.exit("pas de data/labels.jsonl, lancer validation/import_labels.py avant")
    labelled = {json.loads(l)["nct"] for l in LABELS.read_text().splitlines()}
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / (re.sub(r"[^A-Za-z0-9.-]+", "_", args.model) + ".jsonl")
    done = {}
    if out.exists():
        done = {r["nct"]: r for r in map(json.loads, filter(str.strip, out.read_text().splitlines()))}
    pool = sorted(n for n, it in its.items() if "label" not in it and ((n in labelled) == args.eval))
    todo = [n for n in pool if n not in done][: args.limit]
    spent = sum(r.get("cost") or 0 for r in done.values())
    print(f"{out.relative_to(ROOT)} : {len(pool)} essais ({'évaluation' if args.eval else 'corpus'}), "
          f"déjà faits {len(pool) - len([n for n in pool if n not in done])}, à faire {len(todo)}, "
          f"coût cumulé {spent:.3f} $")

    lock = threading.Lock()
    state = {"spent": spent, "stop": False}

    def work(n):
        if state["stop"]:
            return
        try:
            r = classify_openrouter(client, its[n], args.model, args.effort)
        except Skip as e:
            print(f"{n} : raté ({e})", flush=True)
            return
        with lock:
            with out.open("a") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            done[n] = r
            state["spent"] += r.get("cost") or 0
            if args.max_cost and state["spent"] >= args.max_cost:
                state["stop"] = True
                print(f"plafond atteint ({state['spent']:.2f} $), stop", flush=True)

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, todo))
    print(f"coût cumulé : {state['spent']:.3f} $")
    if args.eval:
        agreement({n: done[n] for n in pool if n in done})


if __name__ == "__main__":
    main()
