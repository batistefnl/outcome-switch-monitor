# Règles d'annotation : critères principaux enregistrés vs déposés

Unité : un essai. On compare les critères principaux de la **version de référence** du registre
(dernière version soumise au plus tard le mois de début ; sinon la première version) aux
critères principaux **déposés avec les résultats**. Les titres des critères secondaires déposés
servent uniquement à détecter une rétrogradation.

Cadre : Zarin et al. (2011), éléments d'un critère : domaine, mesure (instrument), métrique
(valeur finale, changement depuis l'inclusion, délai jusqu'à l'événement), méthode d'agrégation
(moyenne, proportion, médiane), délai d'évaluation.

## Verdict (un seul)

- `identique` : mêmes critères, au plus des différences de casse ou de ponctuation, ou un délai
  réexprimé sans contradiction (« 4 weeks » → « Baseline and 4 weeks », « Up to 36 months » → date de
  gel des données) ou une fenêtre de tolérance prolongée par la période de suivi (52 semaines de
  traitement → fin d'étude + 4 semaines).
- `reformulation` : mêmes critères, formulation différente sans effet sur le contenu
  (« Proportion » ↔ « Percentage » ↔ « Number of participants » pour un même événement binaire,
  sigle développé, ordre des mots, simple mention du bras ou de la population d'analyse dans le titre).
- `precision` : le registre était vague et le dépôt précise un élément sans contredire
  l'enregistrement : métrique ajoutée là où aucune n'était indiquée (« Change in… », « Number of
  participants with… », répondeur défini sur l'échelle enregistrée, variation moyenne pour une
  « réponse » non définie : jamais un changement), critère déposé par période, strate, sous-groupe
  ou population d'analyse sans autre changement, critère composite déposé en ses composantes
  enregistrées (PAS et PAD pour « baisse de la PA »).
- `changement` : au moins un élément contredit l'enregistrement ou un critère principal
  apparaît ou disparaît (voir les types).
- `indeterminable` : impossible de juger (pas de critère enregistré, texte inexploitable).

## Types (liste, seulement si verdict = `changement`)

- `supprime` : un critère principal enregistré n'est plus critère principal déposé et n'apparaît pas en secondaire.
  Toujours vérifier les titres secondaires déposés avant de coder `supprime`.
- `retrograde` : un critère principal enregistré apparaît dans les secondaires déposés. Si un nouveau
  critère principal prend sa place : `retrograde` + `ajoute` (pas `remplace`).
- `ajoute` : un nouveau critère principal, absent de l'enregistrement, est déposé
  (les critères de tolérance ajoutés comptent aussi).
- `remplace` : un critère principal enregistré, absent des secondaires déposés, est remplacé par un
  critère d'un autre domaine.
- `delai` : délai d'évaluation différent (12 mois → 6 mois). Pas une simple précision.
- `metrique` : métrique ou agrégation différente (moyenne → proportion, délai jusqu'à
  l'événement → pourcentage, valeur finale → changement depuis l'inclusion quand l'une des deux était explicite).
- `mesure` : instrument ou définition différente (échelle différente, seuil différent,
  composite modifié).

## Gravité (si `changement`)

- `majeur` : `supprime` (y compris d'un critère de tolérance), `remplace`, `retrograde`, ou `ajoute`
  d'un nouveau critère d'efficacité.
- `mineur` : seulement `delai`, `metrique`, `mesure`, ou `ajoute` de tout autre critère (tolérance,
  pharmacocinétique, seuil supplémentaire sur une échelle enregistrée, même critère redéposé sous une
  autre étiquette).
- Cas particulier : un critère enregistré déposé en plus à un autre point temporel ou avec une
  autre agrégation (semaine 52 en plus de la semaine 24, médiane en plus de la moyenne) →
  types `ajoute` + `delai` (ou `metrique`), gravité `mineur`. De même pour le même critère déposé en
  plus pour une autre agence (FDA, PMDA) sur une autre fenêtre ou avec une autre règle de traitement
  de secours : `ajoute` + `delai`, `mineur`. Le retrait d'un point temporel
  ou d'une agrégation d'un critère conservé → `delai` ou `metrique`, `mineur`.

## Principes

- Dans le doute entre `precision` et `changement`, choisir `precision` et l'expliquer dans
  la note : on préfère sous-estimer qu'accuser à tort.
- On ne juge pas si le changement est justifié : ce n'est pas observable ici.
- Note : une phrase, en français, citant l'élément qui motive le verdict.


