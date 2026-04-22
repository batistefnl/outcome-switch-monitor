# paires enregistré / déposé -> data/items.jsonl
import gzip
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def read_gz(p):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def clean(s):
    return " ".join(html.unescape(s or "").split())


def key(s):
    return re.sub(r"[^a-z0-9]+", " ", clean(s).lower()).strip()


def build_item(nct, ref_version):
    ref = read_gz(DATA / "wayback" / nct / f"v{ref_version}.json.gz")
    reg = ref["study"]["protocolSection"].get("outcomesModule", {}).get("primaryOutcomes", [])
    cur = read_gz(DATA / "current" / f"{nct}.json.gz")
    oms = cur.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    dep = [o for o in oms if o.get("type") == "PRIMARY"]
    # titres secondaires : seulement pour voir si un critère a été rétrogradé
    dep_sec = [clean(o["title"]) for o in oms if o.get("type") == "SECONDARY"]
    item = {
        "nct": nct,
        "registered": [{"measure": clean(o["measure"]), "timeFrame": clean(o.get("timeFrame")),
                        "description": clean(o.get("description"))[:400]} for o in reg],
        "deposited": [{"measure": clean(o["title"]), "timeFrame": clean(o.get("timeFrame")),
                       "description": clean(o.get("description"))[:400]} for o in dep],
        "deposited_secondary_titles": dep_sec,
    }
    # identiques après normalisation -> pas besoin de les annoter
    sig = lambda xs: sorted(key(x["measure"]) + "|" + key(x["timeFrame"]) for x in xs)
    if reg and sig(item["registered"]) == sig(item["deposited"]):
        item["label"] = {"verdict": "identique", "by": "auto"}
    return item


def main():
    rows = [json.loads(l) for l in (DATA / "index.jsonl").read_text().splitlines()]
    # on construit tout avant d'écrire, sinon un fichier manquant vide items.jsonl
    its = [build_item(r["nct"], r["ref_version"]) for r in rows if r["status"] == "ok"]
    n = sum("label" in it for it in its)
    (DATA / "items.jsonl").write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in its))
    print(f"essais : {sum(r['status'] == 'ok' for r in rows)} | identiques (auto) : {n}")

if __name__ == "__main__":
    main()
