# Méthode en détail

Les notes complètes, pour ceux que ça intéresse. Les chiffres sortent de `analysis/results.md` et `validation/agreement.md`, qui sont générés par les scripts.

## Corpus

On a pris les essais de phase 3 randomisés et terminés, avec une fin du critère principal entre 2012 et 2022 et des résultats déposés. Ça fait 6 039 essais via l'API v2 de ClinicalTrials.gov. On en garde 5 647 après la perte de 392 enregistrements bruts, dont 5 634 avec un historique complet.

La **version de référence** est la dernière version du registre soumise au plus tard le mois où l'essai commence. 20 % des essais n'ont été enregistrés qu'après leur début : pour eux, on prend la première version et l'essai est marqué « rétrospectif ».

On compare les critères principaux de cette version à ceux déposés avec les résultats. Les titres des critères secondaires déposés servent à repérer un critère principal passé en secondaire. 665 essais sont identiques après normalisation (casse, ponctuation) et sont classés automatiquement. Les 4 969 autres doivent être jugés.

## Verdicts

| Verdict | En gros |
|---|---|
| identique | même critère, à la ponctuation ou à la formulation du délai près |
| reformulation | même critère, autres mots |
| précision | le registre était vague, le dépôt précise sans contredire |
| changement | quelque chose contredit l'enregistrement, ou un critère apparaît / disparaît |
| indéterminable | impossible de juger |

Un changement a un ou plusieurs types : supprimé, rétrogradé, ajouté, remplacé, délai, métrique, mesure. Il a aussi une gravité. Elle est *majeure* pour une suppression, un remplacement, une rétrogradation ou un nouvel objectif d'efficacité, et *mineure* sinon. Dans le doute, la règle dit « précision » plutôt que « changement ». Tout le détail est dans [`classify/GUIDELINES.md`](classify/GUIDELINES.md).

## Échantillon

On a d'abord tiré 500 essais au hasard parmi les non identiques, pré-classés par une IA (ces étiquettes ont été supprimées depuis). Dans ces 500, on a tiré 100 essais en deux strates selon le pré-classement : 50 « changement » et 50 autres. Il en reste 95 après la perte de 5 enregistrements bruts. Chaque essai est pondéré par l'inverse de sa probabilité de tirage ([`validation/design.json`](validation/design.json)). On suppose que la perte des 5 essais est aléatoire au sein des strates.

## Annotation et arbitrage

- **Tour 1** : BF, CM et TJ annotent chacun un tiers avec [`validation/annotate.html`](validation/annotate.html), avec une note pour justifier chaque essai.
- **Tour 2** : en rotation et sans voir le tour 1. TJ reprend la partie de BF, BF celle de CM, CM celle de TJ.
- **Accord avant arbitrage** : 73 % sur la présence d'un changement (kappa 0,44), 52 % sur le verdict détaillé (kappa 0,27). La plupart des désaccords portaient sur la frontière entre reformulation, précision et changement.
- **Règles précisées** en équipe, question par question ([`classify/QUESTIONS.md`](classify/QUESTIONS.md)), puis reportées dans GUIDELINES.md.
- **Arbitrage** des 67 essais en désaccord par AB, qui n'avait pas annoté. 10 décisions contraires aux règles ont été renvoyées en arbitrage et révisées.

Aucune étiquette humaine ne vient d'une IA. `validation/import_labels.py` refuse d'importer tant qu'un désaccord n'est pas arbitré ou qu'une gravité contredit les règles.

## Résultats (essais annotés à la main)

| | Parmi les non identiques | Corpus entier |
|---|---|---|
| Changement de fond | 32 % [23–42] | ≈ 28 % [20–37] |
| Changement majeur | 17 % [11–27] | ≈ 15 % [9–24] |

Ce qui tient à peu près :
- l'ordre de grandeur, que le LLM retrouve aussi sur le reste du corpus ;
- les changements les plus fréquents : ajout d'un critère principal (13 %), rétrogradation (10 %), délai (10 %), métrique (9 %) ;
- plus un essai enregistre de critères principaux, plus il en modifie (OR 2,28 [1,24–4,20] par critère, régression exploratoire).

Ce qu'on ne peut pas conclure :
- industrie contre non industriel (31 % contre 36 %, mais seulement 16 essais non industriels) ;
- avant contre après la Final Rule de 2017 (35 % contre 29 %) ;
- un lien avec la significativité : 92 % des essais avec un changement majeur ont p < 0,05, contre 69 % des autres, mais p = 0,15 avec n = 12.

## Le LLM

| Modèle | Changement oui/non (kappa) | Verdict 4 classes (kappa) | Majeur oui/non (kappa) | « Changement » trouvés (humains : 45) |
|---|---|---|---|---|
| **Gemini 2.5 Flash** (retenu) | 86 % (0,73) | 66 % (0,49) | 89 % (0,70) | 46 |
| Gemini 3 Flash (preview) | 86 % (0,72) | 73 % (0,60) | 93 % (0,80) | 34 |
| DeepSeek V3.2 (n = 89) | 84 % (0,68) | 65 % (0,49) | 85 % (0,59) | 41 |
| GPT-5 mini | 82 % (0,64) | 64 % (0,46) | 88 % (0,70) | 48 |

Gemini 3 Flash a un meilleur accord sur le verdict détaillé, mais il rate un quart des changements. Gemini 2.5 Flash en trouve à peu près autant que les humains, c'est pour ça qu'on l'a gardé.

Sur les 4 874 essais non annotés, pour 3,03 $, il trouve 39 % de changements de fond, dont 15 % majeurs. Le tableau de bord de la démo affiche 40 %, parce qu'il compte aussi les 95 essais annotés.

Le LLM a un biais : sur l'échantillon humain pondéré, il trouve 34 % de changements de fond (contre 32 % pour les humains) et 11 % de changements majeurs (contre 17 %). Il surestime donc probablement le fond et sous-estime le majeur. Ses étiquettes ne servent à aucune des estimations principales.

## Dépendances

`requirements.in` liste les dépendances directes, et `requirements.txt` les fige à la date du 1er avril 2026 :

```bash
uv pip compile requirements.in --python-version 3.12 --exclude-newer 2026-04-01T00:00:00Z -o requirements.txt
```
