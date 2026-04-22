# historique des critères principaux d'un essai, avec les modifs surlignées
# utilisé par le serveur (onglet "version history"), et en ligne de commande :
#   python demo/timeline.py NCT01645787   -> demo/out/<NCT>.html
import html
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collect"))
sys.path.insert(0, str(ROOT / "classify"))
from wayback import get_version, list_versions, read_gz
from build_items import clean

OUT = ROOT / "demo" / "out"
API = "https://clinicaltrials.gov/api/v2/studies/{}"


def primaries(study):
    ps = study["protocolSection"]
    return [(clean(o.get("measure") or o.get("title")), clean(o.get("timeFrame")))
            for o in ps.get("outcomesModule", {}).get("primaryOutcomes", [])]


def word_diff(old, new):
    a, b = old.split(), new.split()
    out = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b).get_opcodes():
        if op == "equal":
            out.append(html.escape(" ".join(b[j1:j2])))
        if op in ("delete", "replace"):
            out.append(f"<del>{html.escape(' '.join(a[i1:i2]))}</del>")
        if op in ("insert", "replace"):
            out.append(f"<ins>{html.escape(' '.join(b[j1:j2]))}</ins>")
    return " ".join(out)


def render_list(prev, cur):
    # chaque critère est comparé au plus proche de la version d'avant
    # en dessous de 0.5 de similarité on considère que c'est un nouveau critère
    rows = []
    for m, tf in cur:
        best = max(prev, key=lambda p: SequenceMatcher(None, p[0], m).ratio(), default=None)
        if best is None or SequenceMatcher(None, best[0], m).ratio() < 0.5:
            rows.append(f"<li class='new'><ins>{html.escape(m)}</ins> <span class='tf'>[{html.escape(tf)}]</span></li>")
        else:
            rows.append(f"<li>{word_diff(best[0], m)} <span class='tf'>[{word_diff(best[1], tf)}]</span></li>")
    for m, tf in prev:
        if max((SequenceMatcher(None, m, c[0]).ratio() for c in cur), default=0) < 0.5:
            rows.append(f"<li class='gone'><del>{html.escape(m)}</del> <span class='tf'>[{html.escape(tf)}]</span></li>")
    return "<ul>" + "".join(rows) + "</ul>"


STYLE = """
:root { --bg:#fafaf9; --panel:#fff; --ink:#1c1917; --muted:#57534e; --line:#e7e5e4;
        --ins:#dcfce7; --ins-ink:#14532d; --del:#fee2e2; --del-ink:#7f1d1d; --accent:#1d4ed8; }
@media (prefers-color-scheme: dark) { :root { --bg:#1c1917; --panel:#292524; --ink:#f5f5f4; --muted:#a8a29e;
        --line:#44403c; --ins:#14532d; --ins-ink:#dcfce7; --del:#7f1d1d; --del-ink:#fee2e2; --accent:#93c5fd; } }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, sans-serif; }
main { max-width: 900px; margin: 0 auto; padding: 16px; }
h1 { font-size: 20px; margin: 8px 0; } .muted, .tf { color: var(--muted); font-size: 13px; }
.card { background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--line); border-radius:8px; padding:10px 14px; margin:10px 0; }
.card.ref { border-left-color: var(--accent); } .card.final { border-left-color: #16a34a; }
ins { background:var(--ins); color:var(--ins-ink); text-decoration:none; padding:0 2px; border-radius:3px; }
del { background:var(--del); color:var(--del-ink); padding:0 2px; border-radius:3px; }
ul { margin:6px 0; padding-left:20px; } .tag { font-size:12px; color:var(--muted); }
"""


class NoHistory(Exception):
    pass


def history(nct, current=None, ref=None):
    """Versions où les critères principaux changent + critères déposés vs version de référence.
    Renvoie des bouts de html déjà prêts (<ins>/<del>)."""
    versions = list_versions(nct)
    if not versions:
        raise NoHistory(nct)
    with ThreadPoolExecutor(4) as ex:
        loaded = dict(zip(sorted(versions), ex.map(lambda n: get_version(nct, n, *versions[n]), sorted(versions))))
    if current is None:
        cur_file = ROOT / "data" / "current" / f"{nct}.json.gz"
        current = read_gz(cur_file) if cur_file.exists() else requests.get(API.format(nct), timeout=60).json()
    st = current["protocolSection"]["statusModule"]
    start = st.get("startDateStruct", {}).get("date", "")
    pc = st.get("primaryCompletionDateStruct", {}).get("date", "")
    idx = {}
    if (ROOT / "data" / "index.jsonl").exists():
        idx = {r["nct"]: r for r in map(json.loads, (ROOT / "data" / "index.jsonl").read_text().splitlines())}
    if ref is None:  # hors corpus il faut la passer en argument
        ref = idx.get(nct, {}).get("ref_version", 0)

    out, prev = [], None
    for n in sorted(loaded):
        v = loaded[n]
        if v is None:
            continue
        p = primaries(v["study"])
        if prev is not None and p == prev and n != ref:
            continue
        sm = v["study"]["protocolSection"]["statusModule"]
        when = sm.get("lastUpdateSubmitDate", "")
        # comparaison au mois près, comme pour la version de référence
        phase = ("before_start" if when[:7] <= start[:7] else
                 "during" if when[:7] <= pc[:7] else "after_primary_completion")
        body = render_list(prev, p) if prev is not None else "<ul>" + "".join(
            f"<li>{html.escape(m)} <span class='tf'>[{html.escape(tf)}]</span></li>" for m, tf in p) + "</ul>"
        out.append({"version": n, "date": when, "status": sm.get("overallStatus", ""), "phase": phase,
                    "is_reference": n == ref, "html": body})
        prev = p

    oms = current.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    dep = [(clean(o["title"]), clean(o.get("timeFrame"))) for o in oms if o.get("type") == "PRIMARY"]
    ref_p = primaries(loaded[ref]["study"]) if loaded.get(ref) else []
    return {"nct": nct, "title": current["protocolSection"]["identificationModule"].get("briefTitle", ""),
            "start": start, "primary_completion": pc, "n_versions": len(versions), "reference": ref,
            "versions": out, "posted_vs_reference": render_list(ref_p, dep) if dep else None}


PHASES_FR = {"before_start": "avant le début", "during": "pendant l'essai",
             "after_primary_completion": "après la fin du critère principal"}


def main():
    nct = sys.argv[1].upper()
    print(f"{nct} : récupération des versions archivées…", flush=True)
    try:
        h = history(nct)
    except NoHistory:
        sys.exit(f"{nct} : aucune version archivée trouvée.")
    label = None
    if (ROOT / "data" / "labels.jsonl").exists():
        label = next((r for r in map(json.loads, (ROOT / "data" / "labels.jsonl").read_text().splitlines())
                      if r["nct"] == nct), None)
    cards = []
    for v in h["versions"]:
        cls = "card ref" if v["is_reference"] else "card"
        tag = " · <b>version de référence</b>" if v["is_reference"] else ""
        cards.append(f"<div class='{cls}'><div class='tag'>Version {v['version']} · {v['date']} · {v['status']} · "
                     f"{PHASES_FR[v['phase']]}{tag}</div>{v['html']}</div>")
    if h["posted_vs_reference"]:
        cards.append(f"<div class='card final'><div class='tag'>Critères principaux déposés avec les résultats, "
                     f"comparés à la version de référence</div>{h['posted_vs_reference']}</div>")
    verdict = ""
    if label:
        verdict = (f"<p><b>Annotation :</b> {html.escape(label['verdict'])}"
                   + (f" ({', '.join(label['types'])} ; {label.get('gravite')})" if label["types"] else "")
                   + f" — {html.escape(label.get('note', ''))}</p>")
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{nct} — historique des critères</title>
<style>{STYLE}</style></head><body><main>
<h1>{nct}</h1><p class="muted">{html.escape(h['title'])}</p>
<p class="muted">Début : {h['start']} · fin du critère principal : {h['primary_completion']} · {h['n_versions']} versions archivées ;
seules les versions où les critères principaux changent sont affichées.
<ins>ajouté</ins> <del>retiré</del>. Une discordance n'est pas en soi une faute : un changement peut être
justifié et déclaré dans la publication.</p>{verdict}{''.join(cards)}
<p class="muted">Source : copies de ClinicalTrials.gov archivées par Internet Archive (février 2025).</p>
</main></body></html>"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{nct}.html").write_text(page)
    print(f"demo/out/{nct}.html ({len(cards)} cartes)")

if __name__ == "__main__":
    main()
