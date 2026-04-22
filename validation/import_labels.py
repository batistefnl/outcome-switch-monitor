# tours 1 et 2 + arbitrage -> data/labels.jsonl (les étiquettes finales)
# si les 2 tours sont d'accord on garde, sinon c'est la décision de l'arbitre
# refuse d'écrire tant qu'il manque une décision ou qu'une étiquette contredit les règles
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "classify"))
from agreement import load, rule_issues, to_review
from batches import TYPES, VERDICTS


def check(r, where):
    e = []
    if r.get("verdict") not in VERDICTS:
        e.append(f"{where} {r.get('nct')} : verdict inconnu {r.get('verdict')!r}")
    if not set(r.get("types") or []) <= TYPES:
        e.append(f"{where} {r.get('nct')} : types inconnus {set(r['types']) - TYPES}")
    if r.get("verdict") == "changement" and r.get("gravite") not in ("majeur", "mineur"):
        e.append(f"{where} {r.get('nct')} : changement sans gravité")
    return e


def main():
    r1, r2 = load("human_labels_*.json"), load("round2/human_labels_*.json")
    sample = [t["nct"] for t in json.loads((HERE / "sample.json").read_text())]
    errors = [f"{n} : absent du tour {k}" for k, d in ((1, r1), (2, r2)) for n in sample if n not in d]
    errors += [m for k, d in (("tour 1", r1), ("tour 2", r2)) for r in d.values() for m in check(r, k)]

    decisions = {}
    files = sorted(f for f in HERE.glob("adjudication*.json") if "revision" not in f.name)
    dec = [d for f in files for d in json.loads(f.read_text())["decisions"]]
    if dec:
        dup = [n for n, c in Counter(d["nct"] for d in dec).items() if c > 1]
        errors += [f"arbitrage {n} : décidé plusieurs fois" for n in dup]
        decisions = {d["nct"]: d for d in dec}
    rev = HERE / "adjudication_revision.json"  # 10 décisions renvoyées à l'arbitre, elles écrasent les premières
    if rev.exists():
        decisions.update({d["nct"]: d for d in json.loads(rev.read_text())["decisions"]})
    review = dict(to_review(r1, r2))
    errors += [f"arbitrage {n} : essai qui n'était pas à arbitrer" for n in decisions if n not in review]
    for d in decisions.values():
        errors += check(d, "arbitrage")
        errors += [f"arbitrage {d['nct']} : {m}" for m in rule_issues(d)]
        if not (d.get("arbitre") or "").strip():
            errors.append(f"arbitrage {d['nct']} : arbitre non renseigné")
    missing = [n for n in review if n not in decisions]
    if missing:
        errors.append(f"{len(missing)} essais à arbitrer sans décision (validation/adjudicate.html) : "
                      + ", ".join(missing[:10]) + (" …" if len(missing) > 10 else ""))
    if errors:
        sys.exit("import refusé :\n" + "\n".join(errors))

    out = []
    for n in sample:
        a, b = r1[n], r2[n]
        src = decisions.get(n, a)
        out.append({"nct": n, "verdict": src["verdict"], "types": src.get("types") or [],
                    "gravite": src.get("gravite"), "note": src.get("note", ""),
                    "annotators": [a["annotator"], b["annotator"]],
                    "source": "arbitrage" if n in decisions else "accord",
                    "arbitre": decisions[n]["arbitre"] if n in decisions else None})
    (ROOT / "data" / "labels.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    print(f"{len(out)} étiquettes -> data/labels.jsonl")
    print(Counter(r["source"] for r in out))
    print(Counter(r["verdict"] for r in out))


if __name__ == "__main__":
    main()
