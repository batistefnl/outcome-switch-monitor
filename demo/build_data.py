# prépare demo/app/data/ : trials.json (1 ligne par essai, pour la recherche) et stats.json (dashboard)
#   python demo/build_data.py [--warm]   # --warm : met en cache l'historique des essais d'exemple
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "demo" / "app" / "data"
sys.path.insert(0, str(ROOT / "classify"))
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "collect"))
from batches import items
from wayback import read_gz

AI_MODEL = "google_gemini-2.5-flash"
FINAL_RULE = "2017-01-18"
TYPE_ORDER = ["retrograde", "supprime", "ajoute", "remplace", "delai", "metrique", "mesure"]


def jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def meta(nct):
    cur = read_gz(DATA / "current" / f"{nct}.json.gz")
    ps = cur["protocolSection"]
    st = ps["statusModule"]
    sp = ps["sponsorCollaboratorsModule"]["leadSponsor"]
    return {"title": ps["identificationModule"].get("briefTitle", ""), "sponsor": sp.get("name", ""),
            "sponsor_class": sp.get("class", ""),
            "start_year": int((st.get("startDateStruct", {}).get("date") or "0")[:4] or 0),
            "primary_completion": (st.get("primaryCompletionDateStruct", {}).get("date") or "")}


def human_estimates():
    # mêmes chiffres que analysis/results.md
    from analyze import N_IDENTICAL, N_NON_IDENTICAL, add_weights, build_table, wprop
    df = build_table()
    add_weights(df)
    w = N_NON_IDENTICAL / (N_NON_IDENTICAL + N_IDENTICAL)
    out = {}
    for col in ("changement", "majeur"):
        p, lo, hi = wprop(df, col)
        out[col] = {"non_identical": [p, lo, hi], "corpus": [w * p, w * lo, w * hi]}
    return out


def agreement(human, files):
    from sklearn.metrics import cohen_kappa_score
    rows = []
    for f in files:
        pred = {r["nct"]: r for r in jsonl(f)}
        ids = [n for n in human if n in pred]
        if not ids:
            continue
        row = {"model": f.stem.replace("_", "/", 1), "n": len(ids)}
        for name, g in (("change", lambda r: r["verdict"] == "changement"), ("verdict", lambda r: r["verdict"]),
                        ("major", lambda r: r["gravite"] == "majeur")):
            x, y = [g(human[n]) for n in ids], [g(pred[n]) for n in ids]
            row[name] = {"accuracy": sum(i == j for i, j in zip(x, y)) / len(ids),
                         "kappa": cohen_kappa_score(x, y) if len(set(x + y)) > 1 else None}
        row["n_change"] = sum(pred[n]["verdict"] == "changement" for n in ids)
        rows.append(row)
    rows.sort(key=lambda r: -(r["change"]["kappa"] or 0))
    return rows


def share(rows, f):
    return {"n": len(rows), "k": sum(1 for r in rows if f(r)), "p": (sum(1 for r in rows if f(r)) / len(rows)) if rows else math.nan}


def main():
    its = items()
    human = {r["nct"]: r for r in jsonl(DATA / "labels.jsonl")}
    ai = {r["nct"]: r for r in jsonl(DATA / "llm_labels" / f"{AI_MODEL}.jsonl")}
    notes_en = {(r["nct"], r["kind"]): r["note_en"] for r in jsonl(DATA / "llm_labels" / "notes_en.jsonl")}
    idx = {r["nct"]: r for r in jsonl(DATA / "index.jsonl")}

    trials = []
    for n, it in its.items():
        m = meta(n)
        t = {"nct": n, **m, "retrospective": bool(idx[n]["retrospective"]),
             "n_registered": len(it["registered"]), "n_posted": len(it["deposited"])}
        if "label" in it:
            t["auto"] = "identique"
        if n in ai:
            a = ai[n]
            t["ai"] = {"verdict": a["verdict"], "types": a["types"], "gravite": a["gravite"], "note": a["note"]}
            if (n, "ai") in notes_en:
                t["ai"]["note_en"] = notes_en[(n, "ai")]
        if n in human:
            h = human[n]
            t["human"] = {k: h.get(k) for k in ("verdict", "types", "gravite", "note", "annotators", "source", "arbitre")}
            if (n, "human") in notes_en:
                t["human"]["note_en"] = notes_en[(n, "human")]  # traduction automatique de la note humaine
        trials.append(t)
    trials.sort(key=lambda t: t["nct"])

    # estimation IA = tous les non identiques, y compris les 95 annotés (d'où 40 % et pas 39 %)
    rows = [t for t in trials if "auto" not in t and "ai" in t]
    chg = lambda t: t["ai"]["verdict"] == "changement"
    maj = lambda t: t["ai"]["gravite"] == "majeur"
    def group(rs, key):
        d = {}
        for t in rs:
            d.setdefault(key(t), []).append(t)
        return d

    by = lambda key: {k: {"change": share(g, chg), "major": share(g, maj)} for k, g in sorted(group(rows, key).items())}
    stats = {
        "counts": {"trials": len(trials), "auto_identical": sum("auto" in t for t in trials),
                   "non_identical": len([t for t in trials if "auto" not in t]),
                   "ai_labelled": len(rows), "human_labelled": len(human)},
        "ai_model": AI_MODEL.replace("_", "/", 1),
        "ai": {"change": share(rows, chg), "major": share(rows, maj),
               "verdicts": Counter(t["ai"]["verdict"] for t in rows),
               "types": {k: share(rows, lambda t, k=k: k in t["ai"]["types"]) for k in TYPE_ORDER},
               "by_sponsor": by(lambda t: "Industry" if t["sponsor_class"] == "INDUSTRY" else "Non-industry"),
               "by_final_rule": by(lambda t: "After Final Rule (2017)" if t["primary_completion"][:10] >= FINAL_RULE
                                   else "Before Final Rule (2017)"),
               "by_start_year": by(lambda t: str(t["start_year"]) if t["start_year"] >= 2006 else "≤2005"),
               "by_registration": by(lambda t: "Registered after start" if t["retrospective"] else "Registered before start")},
        "human": human_estimates(),
        "agreement": agreement(human, sorted(f for f in (DATA / "llm_labels").glob("*.jsonl") if f.name != "notes_en.jsonl")),
    }
    # exemples de la page d'accueil : un essai annoté par type de changement + une précision + une reformulation
    pool = [t for t in trials if "human" in t]
    showcase, used = [], set()
    for ty in TYPE_ORDER:
        c = sorted((t for t in pool if ty in t["human"]["types"] and t["nct"] not in used),
                   key=lambda t: (len(t["human"]["types"]), t["n_registered"] + t["n_posted"]))
        if c:
            showcase.append({"nct": c[0]["nct"], "label": ty})
            used.add(c[0]["nct"])
    for v in ("precision", "reformulation"):
        c = sorted((t for t in pool if t["human"]["verdict"] == v), key=lambda t: t["n_registered"] + t["n_posted"])
        if c:
            showcase.append({"nct": c[0]["nct"], "label": v})
    stats["showcase"] = showcase
    # biais du modèle sur l'échantillon humain (pondéré). recalcule les poids à la main, cf add_weights
    des = json.loads((ROOT / "validation" / "design.json").read_text())
    w = {n: des["stratum_sizes"][h] / sum(v == h for v in des["strata"].values()) for n, h in des["strata"].items()}
    ids = [n for n in human if n in ai]
    W = sum(w[n] for n in ids)
    wp = lambda d, f: sum(w[n] * f(d[n]) for n in ids) / W
    stats["bias"] = {k: {"human": wp(human, f), "ai": wp(ai, f)} for k, f in
                     (("change", lambda r: r["verdict"] == "changement"), ("major", lambda r: r["gravite"] == "majeur"))}
    stats["human_n_change"] = sum(h["verdict"] == "changement" for h in human.values())
    stats["ai"]["cost_usd"] = sum(r.get("cost") or 0 for n, r in ai.items() if n not in human)
    stats["ai"]["kappa_change"] = next((r["change"]["kappa"] for r in stats["agreement"]
                                        if r["model"] == stats["ai_model"]), None)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "trials.json").write_text(json.dumps(trials, ensure_ascii=False, separators=(",", ":")))
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1, default=float))
    c = stats["counts"]
    if "--warm" in sys.argv:  # pour que la démo marche sans réseau
        sys.path.insert(0, str(ROOT / "demo"))
        from timeline import history
        for s in showcase:
            history(s["nct"], ref=idx[s["nct"]]["ref_version"])
            print(f"  historique en cache : {s['nct']}", flush=True)
    print(f"demo/app/data : {c['trials']} essais, {c['auto_identical']} identiques (auto), "
          f"{c['ai_labelled']} étiquettes IA, {c['human_labelled']} étiquettes humaines, "
          f"{len(notes_en)} notes IA en anglais, {len(showcase)} exemples")


if __name__ == "__main__":
    main()
