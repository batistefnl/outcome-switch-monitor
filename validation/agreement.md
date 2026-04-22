# Accord inter-annotateurs

95 essais annotés deux fois, indépendamment (tour 1 / tour 2 en rotation). Kappa de Cohen, IC 95 % par bootstrap (2 000 tirages).

| Niveau | Accord brut | Kappa [IC 95 %] |
|---|---|---|
| Changement oui / non | 73 % | 0.44 [0.25–0.61] |
| Verdict (4 classes) | 52 % | 0.27 [0.13–0.40] |
| Gravité (aucune / mineur / majeur) | 69 % | 0.47 [0.30–0.62] |
| Changement majeur oui / non | 82 % | 0.51 [0.27–0.69] |

Types, parmi les 27 essais jugés « changement » aux deux tours (présence du type chez l'un et l'autre) :

| Type | Tour 1 | Tour 2 | Les deux | Accord brut |
|---|---|---|---|---|
| ajoute | 6 | 6 | 3 | 78 % |
| delai | 14 | 9 | 9 | 81 % |
| mesure | 7 | 1 | 0 | 70 % |
| metrique | 7 | 8 | 6 | 89 % |
| remplace | 2 | 8 | 2 | 78 % |
| retrograde | 12 | 0 | 0 | 56 % |
| supprime | 3 | 6 | 2 | 81 % |

Par paire d'annotateurs (changement oui / non) :

| Tour 1 → tour 2 | n | Accord brut | Kappa |
|---|---|---|---|
| BF → TJ | 31 | 77 % | 0.53 |
| CM → BF | 31 | 65 % | 0.31 |
| TJ → CM | 33 | 76 % | 0.50 |

Matrice des verdicts (lignes : tour 1, colonnes : tour 2) :

| | identique | reformulation | precision | changement |
|---|---|---|---|---|
| **identique** | 0 | 0 | 3 | 0 |
| **reformulation** | 0 | 18 | 7 | 4 |
| **precision** | 0 | 10 | 4 | 6 |
| **changement** | 0 | 8 | 8 | 27 |

Gravité contraire aux règles de GUIDELINES.md (à corriger lors de l'arbitrage) :

- NCT02371759 (tour 2, TJ) : supprime mais gravité mineur
- NCT01062763 (tour 2, TJ) : remplace mais gravité mineur
- NCT00939900 (tour 2, TJ) : gravité majeur sans type majeur
