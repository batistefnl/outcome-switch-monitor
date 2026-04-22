# génère validation/adjudicate.html, la page pour l'arbitre (un seul fichier html, données dedans)
# --revision : renvoie à l'arbitre les essais de revision.txt, avec sa décision d'avant
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from agreement import load, to_review

TEMPLATE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Arbitrage des désaccords</title>
<style>
:root { --bg:#fafaf9; --panel:#ffffff; --ink:#1c1917; --muted:#57534e; --line:#e7e5e4;
        --enr:#eff6ff; --enr-b:#93c5fd; --dep:#f0fdf4; --dep-b:#86efac; --accent:#1d4ed8; --warn:#b45309; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#1c1917; --panel:#292524; --ink:#f5f5f4; --muted:#a8a29e; --line:#44403c;
          --enr:#172554; --enr-b:#1e40af; --dep:#052e16; --dep-b:#166534; --accent:#93c5fd; --warn:#fbbf24; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 16px; }
header { display:flex; flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between; }
h1 { font-size: 18px; margin: 0; }
.progress { color: var(--muted); }
.card { background: var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; margin-top:12px; }
.oc { border-left:4px solid; padding:6px 10px; margin:6px 0; border-radius:4px; }
.enr { background:var(--enr); border-color:var(--enr-b); }
.dep { background:var(--dep); border-color:var(--dep-b); }
.tf, .desc, .sec { color: var(--muted); font-size: 13px; }
h2 { font-size: 15px; margin: 12px 0 4px; }
.labels { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:12px; }
.lab { border:1px solid var(--line); border-radius:8px; padding:10px; }
.lab b { display:block; margin-bottom:4px; }
.warn { color: var(--warn); font-size: 13px; }
fieldset { border:1px solid var(--line); border-radius:8px; margin:10px 0; padding:8px 12px; }
legend { color: var(--muted); font-size: 13px; }
label { margin-right: 14px; display:inline-block; }
textarea, input[type=text] { width:100%; background:var(--bg); color:var(--ink); border:1px solid var(--line); border-radius:6px; padding:6px; font:inherit; }
.nav { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
button { background:var(--panel); color:var(--ink); border:1px solid var(--line); border-radius:6px; padding:8px 14px; font:inherit; cursor:pointer; }
button.primary { background: var(--accent); color: var(--bg); border-color: var(--accent); }
details { margin-top: 8px; font-size: 13px; }
details pre { white-space: pre-wrap; font: 13px/1.5 system-ui, sans-serif; color: var(--muted); }
.done { color: #16a34a; }
</style>
</head>
<body>
<main>
<header>
  <h1>Arbitrage des désaccords — critères principaux</h1>
  <span class="progress" id="progress"></span>
</header>
<div class="card">
  <label style="width:100%">Arbitre (initiales) <input type="text" id="arbitre"></label>
  <details><summary>Règles (classify/GUIDELINES.md)</summary><pre id="rules"></pre></details>
</div>
<div class="card" id="trial"></div>
<div class="card">
  <h2>Décision</h2>
  <fieldset><legend>Verdict</legend><div id="verdicts"></div></fieldset>
  <fieldset id="typesBox"><legend>Types (si changement)</legend><div id="types"></div></fieldset>
  <fieldset id="gravBox"><legend>Gravité (si changement)</legend><div id="grav"></div></fieldset>
  <label style="width:100%">Note (une phrase : ce qui motive la décision)<textarea id="note" rows="2"></textarea></label>
  <div class="nav">
    <button id="prev">← Précédent</button>
    <button class="primary" id="next">Suivant →</button>
    <button id="export">Exporter adjudication.json</button>
  </div>
</div>
</main>
<script>
const DATA = __DATA__;
const RULES = __RULES__;
const VERDICTS = ["identique","reformulation","precision","changement","indeterminable"];
const TYPES = ["supprime","retrograde","ajoute","remplace","delai","metrique","mesure"];
const KEY = __KEY__;
let state = { i: 0, arbitre: "", decisions: {} };
try { const s = localStorage.getItem(KEY); if (s) state = JSON.parse(s); } catch (e) {}
state.i = Math.min(Math.max(state.i || 0, 0), DATA.length - 1);
const IDS = new Set(DATA.map(t => t.nct));
for (const n of Object.keys(state.decisions || {})) if (!IDS.has(n)) delete state.decisions[n];
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };
const esc = s => (s || "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
document.getElementById("rules").textContent = RULES;

function radios(id, name, values) {
  document.getElementById(id).innerHTML = values.map(v =>
    `<label><input type="radio" name="${name}" value="${v}"> ${v}</label>`).join("");
}
radios("verdicts", "verdict", VERDICTS);
radios("grav", "gravite", ["majeur","mineur"]);
document.getElementById("types").innerHTML = TYPES.map(t =>
  `<label><input type="checkbox" value="${t}"> ${t}</label>`).join("");

function oc(cls, o) {
  return `<div class="oc ${cls}"><div>${esc(o.measure)} <span class="tf">[${esc(o.timeFrame)}]</span></div>` +
         (o.description ? `<div class="desc">${esc(o.description)}</div>` : "") + `</div>`;
}
function lab(title, r) {
  const t = r.verdict === "changement" ? ` — ${r.types.join(", ") || "aucun type"} — ${r.gravite || "gravité manquante"}` : "";
  return `<div class="lab"><b>${esc(title)} (${esc(r.annotator || r.arbitre)})</b>${esc(r.verdict)}${esc(t)}<div class="desc">${esc(r.note)}</div></div>`;
}
function render() {
  const t = DATA[state.i];
  const n = Object.keys(state.decisions).length;
  document.getElementById("progress").innerHTML = `Essai ${state.i + 1} / ${DATA.length} — ` +
    `<span class="${n === DATA.length ? "done" : ""}">${n} arbitrés</span>`;
  document.getElementById("arbitre").value = state.arbitre || "";
  document.getElementById("trial").innerHTML = `<b>${t.nct}</b> <span class="warn">${esc(t.reason)}</span>
    <h2>Enregistré (début de l'essai)</h2>${t.registered.map(o => oc("enr", o)).join("") || "<i>aucun</i>"}
    <h2>Déposé avec les résultats</h2>${t.deposited.map(o => oc("dep", o)).join("")}
    <h2>Titres secondaires déposés</h2><div class="sec">${esc(t.deposited_secondary_titles.join(" ; ")) || "—"}</div>
    <h2>Étiquettes existantes</h2><div class="labels">${lab("Tour 1", t.r1)}${lab("Tour 2", t.r2)}${t.prev ? lab("Arbitrage précédent", t.prev) : ""}</div>`;
  const d = state.decisions[t.nct] || {};
  document.querySelectorAll("input[name=verdict]").forEach(r => r.checked = r.value === d.verdict);
  document.querySelectorAll("input[name=gravite]").forEach(r => r.checked = r.value === d.gravite);
  document.querySelectorAll("#types input").forEach(c => c.checked = (d.types || []).includes(c.value));
  document.getElementById("note").value = d.note || "";
  toggle();
  window.scrollTo(0, 0);
}
function toggle() {
  const v = (document.querySelector("input[name=verdict]:checked") || {}).value;
  const on = v === "changement";
  document.getElementById("typesBox").style.opacity = on ? 1 : .4;
  document.getElementById("gravBox").style.opacity = on ? 1 : .4;
}
function store() {
  const t = DATA[state.i];
  const v = (document.querySelector("input[name=verdict]:checked") || {}).value;
  state.arbitre = document.getElementById("arbitre").value;
  if (v) {
    const chg = v === "changement";
    state.decisions[t.nct] = {
      nct: t.nct, verdict: v,
      types: chg ? [...document.querySelectorAll("#types input:checked")].map(c => c.value) : [],
      gravite: chg ? ((document.querySelector("input[name=gravite]:checked") || {}).value || null) : null,
      note: document.getElementById("note").value,
      arbitre: state.arbitre,
    };
  }
  save();
}
document.getElementById("verdicts").addEventListener("change", toggle);
document.getElementById("next").onclick = () => { store(); if (state.i < DATA.length - 1) state.i++; save(); render(); };
document.getElementById("prev").onclick = () => { store(); if (state.i > 0) state.i--; save(); render(); };
document.getElementById("export").onclick = () => {
  store();
  const out = { decisions: DATA.map(t => state.decisions[t.nct]).filter(Boolean) };
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: "application/json" }));
  a.download = __OUT__; a.click();
};
render();
</script>
</body>
</html>
"""


def main():
    r1, r2 = load("human_labels_*.json"), load("round2/human_labels_*.json")
    sample = {t["nct"]: t for t in json.loads((HERE / "sample.json").read_text())}
    js = lambda x: json.dumps(x, ensure_ascii=False).replace("</", "<\\/")
    rules = (ROOT / "classify" / "GUIDELINES.md").read_text()
    data = []
    if "--revision" in sys.argv:
        prev = {d["nct"]: d for f in sorted(HERE.glob("adjudication.json")) for d in json.loads(f.read_text())["decisions"]}
        for line in (HERE / "revision.txt").read_text().splitlines():
            n, _, why = line.partition("#")
            if n.strip():
                data.append({**sample[n.strip()], "reason": "Renvoyé à l'arbitre : " + why.strip(),
                             "r1": r1[n.strip()], "r2": r2[n.strip()], "prev": prev.get(n.strip())})
        page, key, out = "adjudicate_revision.html", "adjudication-revision-v1", "adjudication_revision.json"
    else:
        for n, reason in to_review(r1, r2):
            data.append({**sample[n], "reason": reason, "r1": r1[n], "r2": r2[n]})
        page, key, out = "adjudicate.html", "adjudication-v1", "adjudication.json"
    html = TEMPLATE
    for k, v in (("__DATA__", data), ("__RULES__", rules), ("__KEY__", key), ("__OUT__", out)):
        html = html.replace(k, js(v))
    (HERE / page).write_text(html)
    print(f"validation/{page} ({len(data)} essais à arbitrer)")


if __name__ == "__main__":
    main()
