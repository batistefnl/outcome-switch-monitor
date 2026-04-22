# accord entre les 2 tours (kappa) + liste des désaccords à arbitrer
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "classify"))
from batches import TYPES, fmt_item, items

MAJOR = {"supprime", "remplace", "retrograde"}


def load(pattern):
    out = {}
    for f in sorted(HERE.glob(pattern)):
        exp = json.loads(f.read_text())
        for r in exp["labels"]:
            out[r["nct"]] = {**r, "annotator": exp["annotator"]}
    return out


def kappa_ci(x, y, n_boot=2000, seed=0):
    x, y = np.asarray(x), np.asarray(y)
    k = cohen_kappa_score(x, y)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        i = rng.integers(0, len(x), len(x))
        if len(set(x[i]) | set(y[i])) > 1:
            boots.append(cohen_kappa_score(x[i], y[i]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return k, lo, hi


def rule_issues(r):
    # gravité incohérente avec les types. on ne vérifie pas `ajoute`, ça dépend du critère ajouté
    if r["verdict"] != "changement":
        return []
    t = set(r["types"])
    if t & MAJOR and r["gravite"] != "majeur":
        return [f"{'/'.join(sorted(t & MAJOR))} mais gravité {r['gravite']}"]
    if not t & MAJOR and "ajoute" not in t and r["gravite"] == "majeur":
        return ["gravité majeur sans type majeur"]
    return []


def same(a, b):
    return (a["verdict"], sorted(a["types"]), a["gravite"]) == (b["verdict"], sorted(b["types"]), b["gravite"])


def to_review(r1, r2):
    """Essais à arbitrer + la raison. Les désaccords changement oui/non d'abord."""
    ids = [n for n in r1 if n in r2]
    chg = lambda r: r["verdict"] == "changement"
    out = [(n, "Désaccord sur la présence d'un changement") for n in ids if chg(r1[n]) != chg(r2[n])]
    out += [(n, "Désaccord sur le verdict, les types ou la gravité") for n in ids
            if chg(r1[n]) == chg(r2[n]) and not same(r1[n], r2[n])]
    out += [(n, "Accord, mais gravité contraire aux règles : " + "; ".join(rule_issues(r1[n]))) for n in ids
            if same(r1[n], r2[n]) and rule_issues(r1[n])]
    # rajouté après avoir tranché QUESTIONS.md : des essais où on était d'accord mais selon l'ancienne règle
    extra = HERE / "review_extra.txt"
    if extra.exists():
        listed = {l.split("#")[0].strip() for l in extra.read_text().splitlines()} - {""}
        out += [(n, "Accord, renvoyé à l'arbitrage (review_extra.txt)") for n in ids
                if n in listed and n not in {m for m, _ in out}]
    return out


def fmt_label(r):
    s = r["verdict"]
    if r["verdict"] == "changement":
        s += f" — {', '.join(r['types'])} — {r['gravite']}"
    return s


def main():
    r1, r2 = load("human_labels_*.json"), load("round2/human_labels_*.json")
    ids = [n for n in r1 if n in r2]
    if not ids:
        sys.exit("rien d'annoté aux deux tours")
    a, b = [r1[n] for n in ids], [r2[n] for n in ids]
    L = ["# Accord inter-annotateurs", "",
         f"{len(ids)} essais annotés deux fois, indépendamment (tour 1 / tour 2 en rotation). "
         "Kappa de Cohen, IC 95 % par bootstrap (2 000 tirages).", "",
         "| Niveau | Accord brut | Kappa [IC 95 %] |", "|---|---|---|"]
    levels = [
        ("Changement oui / non", lambda r: r["verdict"] == "changement"),
        ("Verdict (4 classes)", lambda r: r["verdict"]),
        ("Gravité (aucune / mineur / majeur)", lambda r: r["gravite"] or "aucune"),
        ("Changement majeur oui / non", lambda r: r["gravite"] == "majeur"),
    ]
    for name, f in levels:
        x, y = [f(r) for r in a], [f(r) for r in b]
        acc = np.mean([i == j for i, j in zip(x, y)])
        k, lo, hi = kappa_ci(x, y)
        L.append(f"| {name} | {100 * acc:.0f} % | {k:.2f} [{lo:.2f}–{hi:.2f}] |")

    both = [n for n in ids if r1[n]["verdict"] == r2[n]["verdict"] == "changement"]
    L += ["", f"Types, parmi les {len(both)} essais jugés « changement » aux deux tours "
          "(présence du type chez l'un et l'autre) :", "",
          "| Type | Tour 1 | Tour 2 | Les deux | Accord brut |", "|---|---|---|---|---|"]
    for t in sorted(TYPES):
        x = [t in r1[n]["types"] for n in both]
        y = [t in r2[n]["types"] for n in both]
        L.append(f"| {t} | {sum(x)} | {sum(y)} | {sum(i and j for i, j in zip(x, y))} | "
                 f"{100 * np.mean([i == j for i, j in zip(x, y)]):.0f} % |")

    L += ["", "Par paire d'annotateurs (changement oui / non) :", "",
          "| Tour 1 → tour 2 | n | Accord brut | Kappa |", "|---|---|---|---|"]
    for (p, q), ns in sorted(Counter((r1[n]["annotator"], r2[n]["annotator"]) for n in ids).items()):
        sub = [n for n in ids if (r1[n]["annotator"], r2[n]["annotator"]) == (p, q)]
        x = [r1[n]["verdict"] == "changement" for n in sub]
        y = [r2[n]["verdict"] == "changement" for n in sub]
        k = cohen_kappa_score(x, y) if len(set(x + y)) > 1 else float("nan")
        L.append(f"| {p} → {q} | {ns} | {100 * np.mean([i == j for i, j in zip(x, y)]):.0f} % | {k:.2f} |")

    L += ["", "Matrice des verdicts (lignes : tour 1, colonnes : tour 2) :", ""]
    V = ["identique", "reformulation", "precision", "changement", "indeterminable"]
    V = [v for v in V if any(r["verdict"] == v for r in a + b)]
    m = Counter((r1[n]["verdict"], r2[n]["verdict"]) for n in ids)
    L += ["| | " + " | ".join(V) + " |", "|---" * (len(V) + 1) + "|"]
    L += [f"| **{u}** | " + " | ".join(str(m[(u, v)]) for v in V) + " |" for u in V]

    issues = [(n, t, r) for t, d in (("tour 1", r1), ("tour 2", r2)) for n in ids for r in [d[n]] if rule_issues(r)]
    if issues:
        L += ["", "Gravité contraire aux règles de GUIDELINES.md (à corriger lors de l'arbitrage) :", ""]
        L += [f"- {n} ({t}, {r['annotator']}) : {'; '.join(rule_issues(r))}" for n, t, r in issues]
    (HERE / "agreement.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))

    its = items()
    review = to_review(r1, r2)
    D = ["# Essais à arbitrer", "",
         f"{len(review)} essais sur {len(ids)} : "
         + ", ".join(f"{c} — {k.split(' :')[0].lower()}" for k, c in Counter(r for _, r in review).items()) + ". "
         "Les deux annotateurs discutent ; à défaut d'accord, le troisième tranche. "
         "Saisie des décisions : validation/adjudicate.html (build_adjudicate.py).", ""]
    for n, reason in review:
        D += [f"## {n}", "", f"*{reason}*", "", "```", fmt_item(its[n]).rstrip(), "```", "",
              f"- **Tour 1 ({r1[n]['annotator']})** : {fmt_label(r1[n])}. {r1[n]['note']}",
              f"- **Tour 2 ({r2[n]['annotator']})** : {fmt_label(r2[n])}. {r2[n]['note']}", ""]
    (HERE / "disagreements.md").write_text("\n".join(D))
    print(f"\n{len(review)} essais à arbitrer -> validation/disagreements.md")


if __name__ == "__main__":
    main()
