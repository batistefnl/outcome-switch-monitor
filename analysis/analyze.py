# stats sur les 95 essais annotés à la main -> analysis/table.csv et analysis/results.md
import gzip
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "analysis"
N_NON_IDENTICAL, N_IDENTICAL = 4969, 665  # en dur, cf sortie de build_items.py
FINAL_RULE = "2017-01-18"


def read_gz(p):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def wilson(k, n, z=1.96):
    if n == 0:
        return (math.nan, math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


def parse_p(s):
    # les p-valeurs déposées sont du texte libre : "<0.001", "0.032", ...
    m = re.search(r"(\d*\.?\d+(?:[eE]-?\d+)?)", s or "")
    return float(m.group(1)) if m else None


def build_table():
    idx = {r["nct"]: r for r in map(json.loads, (DATA / "index.jsonl").read_text().splitlines())}
    rows = []
    labels = list(map(json.loads, (DATA / "labels.jsonl").read_text().splitlines()))
    for lab in labels:
        if lab["verdict"] == "indeterminable":
            continue
        nct = lab["nct"]
        cur = read_gz(DATA / "current" / f"{nct}.json.gz")
        ps = cur["protocolSection"]
        st = ps["statusModule"]
        prim = [o for o in cur.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
                if o.get("type") == "PRIMARY"]
        pvals = [parse_p(a.get("pValue")) for o in prim for a in o.get("analyses", []) if a.get("pValue")]
        pvals = [p for p in pvals if p is not None]
        ref = read_gz(DATA / "wayback" / nct / f"v{idx[nct]['ref_version']}.json.gz")
        n_reg = len(ref["study"]["protocolSection"].get("outcomesModule", {}).get("primaryOutcomes", []))
        sponsor = ps["sponsorCollaboratorsModule"]["leadSponsor"].get("class")
        rows.append({
            "nct": nct,
            "verdict": lab["verdict"],
            "changement": int(lab["verdict"] == "changement"),
            "majeur": int(lab.get("gravite") == "majeur"),
            "types": "|".join(lab.get("types", [])),
            "industrie": int(sponsor == "INDUSTRY"),
            "sponsor_class": sponsor,
            "start_year": int(st.get("startDateStruct", {}).get("date", "0000")[:4]),
            "primary_completion": st.get("primaryCompletionDateStruct", {}).get("date", ""),
            "enrollment": ps.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
            "retrospectif": int(idx[nct]["retrospective"]),
            "n_reg_primary": n_reg,
            "n_versions": idx[nct]["n_versions"],
            "has_pvalue": int(bool(pvals)),
            "significatif": int(bool(pvals) and min(pvals) < 0.05),
        })
    df = pd.DataFrame(rows)
    df.attrs["n_annotated"] = len(labels)
    df["post_final_rule"] = (df["primary_completion"].str[:10] >= FINAL_RULE).astype(int)
    df["log_enrollment"] = np.log1p(df["enrollment"].fillna(df["enrollment"].median()))
    return df


def add_weights(df):
    """Poids de sondage = taille de la strate / nb d'essais tirés dans la strate (design.json)."""
    design_file = ROOT / "validation" / "design.json"
    if not design_file.exists():
        df["w"] = 1.0
        return None
    design = json.loads(design_file.read_text())
    df["strate"] = df.nct.map(design["strata"])
    drawn = pd.Series(design["strata"]).value_counts()
    df["w"] = df.strate.map(lambda h: design["stratum_sizes"][h] / drawn[h])
    return design


def wprop(g, col):
    # proportion pondérée, IC de Wilson sur l'effectif efficace de Kish
    if len(g) == 0:
        return math.nan, math.nan, math.nan
    p = (g.w * g[col]).sum() / g.w.sum()
    n_eff = g.w.sum() ** 2 / (g.w ** 2).sum()
    _, lo, hi = wilson(p * n_eff, n_eff)
    return p, lo, hi


def fmt(p, lo, hi):
    return f"{100 * p:.0f} % [{100 * lo:.0f}–{100 * hi:.0f}]" if not math.isnan(p) else "—"


def main():
    df = build_table()
    design = add_weights(df)
    df.to_csv(OUT / "table.csv", index=False)
    n = len(df)
    w = N_NON_IDENTICAL / (N_NON_IDENTICAL + N_IDENTICAL)
    L = ["# Résultats", "", f"Échantillon évaluable : **{n} essais** ({df.attrs['n_annotated']} annotés à la main, "
         f"{df.attrs['n_annotated'] - n} indéterminables exclus).", ""]
    if design:
        L += ["Échantillon stratifié (50 essais pré-classés « changement » par un agent IA, 50 autres) : "
              "proportions et régressions **pondérées** par l'inverse de la probabilité de tirage "
              f"(strates de {design['stratum_sizes']['changement']} et {design['stratum_sizes']['autre']} essais), "
              "IC de Wilson sur l'effectif efficace de Kish. Les effectifs n sont bruts.", ""]

    L += ["## Prévalence", "", "| | Parmi les essais non identiques | Corpus (pondéré, identiques réintégrés) |", "|---|---|---|"]
    for col, name in (("changement", "Changement de fond"), ("majeur", "Changement majeur")):
        p, lo, hi = wprop(df, col)
        L.append(f"| {name} | {fmt(p, lo, hi)} | {fmt(w * p, w * lo, w * hi)} |")
    L += ["", "Types (un essai peut en cumuler plusieurs ; n brut, % pondéré) :", ""]
    types = df["types"].fillna("").str.split("|").explode()
    for t, c in types[types != ""].value_counts().items():
        df["_t"] = df["types"].fillna("").str.split("|").apply(lambda xs: int(t in xs))
        L.append(f"- {t} : {c} ({100 * wprop(df, '_t')[0]:.0f} % des essais)")
    df.drop(columns="_t", inplace=True, errors="ignore")

    L += ["", "## Par sous-groupe", "", "| Sous-groupe | n | Changement de fond | Changement majeur |", "|---|---|---|---|"]
    groups = [("Industrie", df.industrie == 1), ("Non industriel", df.industrie == 0),
              ("Enregistré avant le début", df.retrospectif == 0), ("Enregistré après le début", df.retrospectif == 1),
              ("Fin du critère principal avant la Final Rule (18/01/2017)", df.post_final_rule == 0),
              ("Fin du critère principal après la Final Rule", df.post_final_rule == 1)]
    for name, m in groups:
        s = df[m]
        L.append(f"| {name} | {len(s)} | {fmt(*wprop(s, 'changement'))} | {fmt(*wprop(s, 'majeur'))} |")

    L += ["", "## Régression logistique", "",
          "Modèle : changement ~ industrie + année de début (centrée) + log(effectif) + enregistrement rétrospectif "
          "+ nombre de critères principaux enregistrés. Pondérée par les poids de sondage, erreurs-types robustes. "
          "Pas d'effets aléatoires par promoteur : la plupart des promoteurs n'ont qu'un ou deux essais dans "
          "l'échantillon. Effectif faible : à lire comme exploratoire.", ""]
    df["start_c"] = df.start_year - df.start_year.median()
    fw = df.w * len(df) / df.w.sum()
    for y in ("changement", "majeur"):
        fit = smf.glm(f"{y} ~ industrie + start_c + log_enrollment + retrospectif + n_reg_primary", df,
                      family=sm.families.Binomial(), freq_weights=fw).fit(cov_type="HC0")
        ci = fit.conf_int()
        L += [f"**{y}** (n = {n})", "", "| Variable | Odds ratio | IC 95 % | p |", "|---|---|---|---|"]
        for v in fit.params.index[1:]:
            L.append(f"| {v} | {math.exp(fit.params[v]):.2f} | {math.exp(ci.loc[v, 0]):.2f}–{math.exp(ci.loc[v, 1]):.2f} | {fit.pvalues[v]:.3f} |")
        L.append("")

    L += ["## Lien avec la significativité du critère principal déposé", ""]
    s = df[df.has_pvalue == 1]
    L.append(f"Essais avec au moins une p-valeur déposée sur un critère principal : {len(s)} / {n}.")
    L += ["", "| | n | Au moins un critère principal p < 0,05 (pondéré) |", "|---|---|---|"]
    for name, m in (("Changement de fond", s.changement == 1), ("Pas de changement", s.changement == 0),
                    ("Changement majeur", s.majeur == 1), ("Pas de changement majeur", s.majeur == 0)):
        g = s[m]
        L.append(f"| {name} | {len(g)} | {fmt(*wprop(g, 'significatif'))} |")
    for col in ("changement", "majeur"):
        tab = pd.crosstab(s[col], s.significatif).reindex(index=[0, 1], columns=[0, 1], fill_value=0)
        odds, p = fisher_exact(tab.values)
        L.append(f"\nTest exact de Fisher ({col} × significatif, effectifs bruts non pondérés) : OR = {odds:.2f}, p = {p:.3f}")
    L += ["", "Ces p-valeurs portent sur les analyses déposées dans ClinicalTrials.gov, pas sur les articles ; "
          "un essai peut déposer plusieurs comparaisons, on retient la plus petite.", ""]
    (OUT / "results.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
