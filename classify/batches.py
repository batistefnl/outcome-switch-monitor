# trucs communs à classify/ et validation/
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ITEMS = DATA / "items.jsonl"
VERDICTS = {"identique", "reformulation", "precision", "changement", "indeterminable"}
TYPES = {"supprime", "retrograde", "ajoute", "remplace", "delai", "metrique", "mesure"}


def items():
    return {i["nct"]: i for i in map(json.loads, ITEMS.read_text().splitlines())}


def fmt_item(it):
    # même contenu que ce que voient les annotateurs, important pour comparer humains / LLM
    lines = [f"### {it['nct']}"]
    for tag, xs in (("ENR", it["registered"]), ("DEP", it["deposited"])):
        for x in xs:
            d = f" — {x['description']}" if x["description"] else ""
            lines.append(f"{tag}: {x['measure']} [{x['timeFrame']}]{d}")
    lines.append("SEC: " + "; ".join(it["deposited_secondary_titles"]))
    return "\n".join(lines) + "\n"
