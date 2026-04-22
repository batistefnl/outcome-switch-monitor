# figure du README, lit table.csv (lancer analyze.py avant)
# à lancer depuis analysis/ à cause de l'import
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from analyze import wprop

HERE = Path(__file__).resolve().parent

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
MAJEUR, MINEUR = "#2a78d6", "#eb6834"  # mêmes couleurs que la démo


def main():
    df = pd.read_csv(HERE / "table.csv")
    groups = [("Tous les essais", df),
              ("Industrie", df[df.industrie == 1]),
              ("Non industriel", df[df.industrie == 0]),
              ("Fin avant la Final Rule (2017)", df[df.post_final_rule == 0]),
              ("Fin après la Final Rule (2017)", df[df.post_final_rule == 1])]
    groups = groups[::-1]  # barh part du bas

    fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    h = 0.55
    top = 0
    for i, (name, g) in enumerate(groups):
        n = len(g)
        maj = 100 * wprop(g, "majeur")[0]
        tot, lo, hi = wprop(g, "changement")
        tot *= 100
        ax.barh(i, maj, height=h, color=MAJEUR, edgecolor=SURFACE, linewidth=2)
        ax.barh(i, tot - maj, left=maj, height=h, color=MINEUR, edgecolor=SURFACE, linewidth=2)
        ax.plot([100 * lo, 100 * hi], [i, i], color=INK_2, linewidth=1.2, solid_capstyle="butt")
        ax.text(100 * hi + 1.2, i, f"{tot:.0f} %", va="center", fontsize=9.5, color=INK)
        top = max(top, 100 * hi)
        ax.text(-1.5, i, f"{name}  (n = {n})", va="center", ha="right", fontsize=9.5, color=INK)

    xmax = 10 * (int(top + 8) // 10 + 1)  # +8 pour que le label du plus grand IC rentre
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.6, len(groups) - 0.4)
    ax.set_yticks([])
    ax.set_xticks(range(0, xmax + 1, 10))
    ax.set_xticklabels([f"{x} %" for x in range(0, xmax + 1, 10)], fontsize=8.5, color=INK_2)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)

    fig.text(0.02, 0.95, "Changement de fond du critère principal entre l'enregistrement et les résultats déposés",
             fontsize=11.5, color=INK, weight="bold")
    fig.text(0.02, 0.895, f"Phase 3 randomisés terminés (2012-2022), {len(df)} essais non identiques annotés "
             "à la main, pondérés ; barre grise : IC 95 %", fontsize=8.5, color=INK_2)
    handles = [plt.Rectangle((0, 0), 1, 1, color=MAJEUR), plt.Rectangle((0, 0), 1, 1, color=MINEUR)]
    fig.legend(handles, ["Changement majeur (supprimé, remplacé, rétrogradé, efficacité ajoutée)",
                         "Changement mineur (délai, métrique, définition)"],
               loc="lower left", bbox_to_anchor=(0.02, 0.0), ncol=1, frameon=False, fontsize=8.5,
               labelcolor=INK_2, handlelength=1.2)
    fig.subplots_adjust(left=0.36, right=0.97, top=0.84, bottom=0.21)
    fig.savefig(HERE / "figure.png", facecolor=SURFACE)
    print("analysis/figure.png")


if __name__ == "__main__":
    main()
