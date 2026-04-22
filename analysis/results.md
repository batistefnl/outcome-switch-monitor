# Résultats

Échantillon évaluable : **95 essais** (95 annotés à la main, 0 indéterminables exclus).

Échantillon stratifié (50 essais pré-classés « changement » par un agent IA, 50 autres) : proportions et régressions **pondérées** par l'inverse de la probabilité de tirage (strates de 155 et 339 essais), IC de Wilson sur l'effectif efficace de Kish. Les effectifs n sont bruts.

## Prévalence

| | Parmi les essais non identiques | Corpus (pondéré, identiques réintégrés) |
|---|---|---|
| Changement de fond | 32 % [23–42] | 28 % [20–37] |
| Changement majeur | 17 % [11–27] | 15 % [9–24] |

Types (un essai peut en cumuler plusieurs ; n brut, % pondéré) :

- ajoute : 18 (13 % des essais)
- retrograde : 16 (10 % des essais)
- delai : 16 (10 % des essais)
- metrique : 11 (9 % des essais)
- supprime : 9 (7 % des essais)
- mesure : 7 (5 % des essais)
- remplace : 1 (1 % des essais)

## Par sous-groupe

| Sous-groupe | n | Changement de fond | Changement majeur |
|---|---|---|---|
| Industrie | 79 | 31 % [21–43] | 15 % [8–25] |
| Non industriel | 16 | 36 % [16–61] | 28 % [11–54] |
| Enregistré avant le début | 71 | 32 % [21–44] | 15 % [8–26] |
| Enregistré après le début | 24 | 33 % [17–54] | 22 % [9–43] |
| Fin du critère principal avant la Final Rule (18/01/2017) | 51 | 35 % [22–49] | 18 % [10–32] |
| Fin du critère principal après la Final Rule | 44 | 29 % [17–44] | 16 % [7–30] |

## Régression logistique

Modèle : changement ~ industrie + année de début (centrée) + log(effectif) + enregistrement rétrospectif + nombre de critères principaux enregistrés. Pondérée par les poids de sondage, erreurs-types robustes. Pas d'effets aléatoires par promoteur : la plupart des promoteurs n'ont qu'un ou deux essais dans l'échantillon. Effectif faible : à lire comme exploratoire.

**changement** (n = 95)

| Variable | Odds ratio | IC 95 % | p |
|---|---|---|---|
| industrie | 1.33 | 0.35–5.09 | 0.673 |
| start_c | 0.88 | 0.74–1.03 | 0.115 |
| log_enrollment | 0.96 | 0.64–1.44 | 0.858 |
| retrospectif | 0.81 | 0.25–2.63 | 0.727 |
| n_reg_primary | 2.28 | 1.24–4.20 | 0.008 |

**majeur** (n = 95)

| Variable | Odds ratio | IC 95 % | p |
|---|---|---|---|
| industrie | 0.69 | 0.13–3.59 | 0.662 |
| start_c | 0.88 | 0.69–1.13 | 0.314 |
| log_enrollment | 0.99 | 0.61–1.58 | 0.951 |
| retrospectif | 1.17 | 0.24–5.64 | 0.843 |
| n_reg_primary | 2.14 | 1.13–4.05 | 0.019 |

## Lien avec la significativité du critère principal déposé

Essais avec au moins une p-valeur déposée sur un critère principal : 56 / 95.

| | n | Au moins un critère principal p < 0,05 (pondéré) |
|---|---|---|
| Changement de fond | 25 | 75 % [54–88] |
| Pas de changement | 31 | 71 % [53–85] |
| Changement majeur | 12 | 92 % [64–99] |
| Pas de changement majeur | 44 | 69 % [53–81] |

Test exact de Fisher (changement × significatif, effectifs bruts non pondérés) : OR = 1.05, p = 1.000

Test exact de Fisher (majeur × significatif, effectifs bruts non pondérés) : OR = 5.69, p = 0.147

Ces p-valeurs portent sur les analyses déposées dans ClinicalTrials.gov, pas sur les articles ; un essai peut déposer plusieurs comparaisons, on retient la plus petite.
