# Questions de règles à trancher avant l'arbitrage

Points où GUIDELINES.md laisse place à plusieurs lectures, d'après les désaccords entre les deux tours
d'annotation (`validation/disagreements.md`). Les réponses sont à décider par l'équipe et à reporter dans
GUIDELINES.md ; les essais cités servent d'exemples, ils ne sont pas tranchés ici.

## 1. Frontière reformulation / précision

18 essais passent de l'une à l'autre entre les deux tours ; les deux tours ne concordent que sur 4 « précision ».

- Passer d'une proportion à un nombre de participants (ou l'inverse), ou ajouter « change from baseline » à
  une mesure sans métrique : reformulation ou précision ? (NCT04051463, NCT04668950, NCT01686633, NCT01235234)
- Préciser la méthode d'analyse (Kaplan-Meier, MMRM) ou la population (ITT) : reformulation ou précision ?
  (NCT01492101, NCT02431806, NCT02322775)
- Une information présente dans la description enregistrée et reprise dans le titre déposé : reformulation
  ou précision ? (NCT01533428)

## 2. Délai exprimé autrement

- « Up to 36 months » → date de gel des données ; « 4 weeks » → « Baseline and 4 weeks » : les 3 essais
  « identique » du tour 1 sont « précision » au tour 2 (NCT03474107, NCT03345342, NCT01313767). Une
  différence de délai, même sans contradiction, exclut-elle « identique » ?
- Fenêtre de tolérance allongée par une période de suivi (52 semaines → fin d'étude + 4 semaines) :
  `delai` ou précision ? (NCT03700320)

## 3. Échelle continue → répondeur défini sur la même échelle

MADRS → réponse définie par une baisse de plus de 50 % du MADRS ; « clinical response » en MAVC → variation
moyenne de la MAVC : précision (registre vague), `metrique` ou `remplace` ? (NCT01429272, NCT04739306)

## 4. Ancien critère principal retrouvé en secondaire

Le tour 2 n'a jamais utilisé `retrograde` (12 fois au tour 1), y compris quand sa note mentionne le passage en
secondaire (NCT03083665). À préciser :

- Faut-il toujours vérifier les titres secondaires déposés avant de coder `supprime` ?
- Quand un nouveau critère prend la place d'un ancien qui passe en secondaire : `retrograde` + `ajoute`,
  `remplace` + `retrograde`, ou `remplace` seul ? (NCT01473589, NCT03504423, NCT00545532, NCT04870606,
  NCT02062463, NCT02611687, NCT01346592)

## 5. Critère découpé en plusieurs critères déposés

- Composantes (PAS et PAD pour « baisse de la PA ») : précision (règle actuelle) ou `remplace` ? (NCT01062763)
- Même critère déposé par strate, par population ou par sous-groupe : reformulation, précision ou `ajoute` ?
  (NCT02105948, NCT03257267, NCT01439360)
- Critère déposé à la fois au titre de l'efficacité et de la tolérance : `ajoute` ? (NCT01144338)

## 6. Critères ajoutés pour une autre autorité (FDA, PMDA)

Même critère sur une autre fenêtre ou avec une autre règle de traitement de secours, déposé en plus pour une
autre agence : `ajoute` + `delai` (mineur, règle du point temporel ajouté), `ajoute` + `mesure`, ou `ajoute`
d'efficacité (majeur) ? (NCT02278341, NCT01887600, NCT02706873)

## 7. Gravité d'un `ajoute` qui n'est ni efficacité ni tolérance

Critère pharmacocinétique, psychométrique ou seuil supplémentaire sur une échelle déjà enregistrée :
mineur ou majeur ? (NCT03735121, NCT02276274)

## 8. Gravité : rappels

Trois étiquettes du tour 2 contredisent la règle actuelle (`supprime`/`remplace` en mineur, majeur sans type
majeur : NCT02371759, NCT01062763, NCT00939900). L'import final refuse ces combinaisons ; si la règle doit
changer (par exemple `supprime` d'un critère de tolérance seul en mineur), modifier GUIDELINES.md et
`rule_issues` dans `validation/agreement.py`.

## Après décision

Si une règle change, elle vaut aussi pour les 32 essais où les deux tours concordent : vérifier qu'ils la
respectent avant l'import final. Un essai concordant à revoir s'ajoute à l'arbitrage en inscrivant son NCT
dans `validation/review_extra.txt`, puis en relançant `validation/build_adjudicate.py`.

## Décisions de l'équipe

- Q1 : critère enregistré sans métrique, dépôt qui ajoute une métrique (« Change in… », « Number of participants with… ») = précision (règle actuelle confirmée ; ex. NCT04051463, NCT04668950, NCT01235234).
- Q3 : échelle ou notion de réponse enregistrée sans métrique, dépôt qui fixe une métrique (répondeur sur l'échelle, variation moyenne) = précision, jamais changement (NCT01429272, NCT04739306).
- Q5 : critère déposé par strate, sous-groupe ou population d’analyse, sans autre changement = précision (règle actuelle confirmée ; ex. NCT02105948, NCT03257267, NCT03836807).
- Q4 : ancien critère principal retrouvé dans les titres secondaires déposés, nouveau critère à sa place = `retrograde` + `ajoute` (pas `remplace`) ; `supprime` seulement si l’ancien critère est absent des secondaires (ex. NCT03504423, NCT00545532).
- Q2 : délai réexprimé sans contradiction (« 4 weeks » → « Baseline and 4 weeks », « Up to 36 months » → date de gel) = identique ; la définition de `identique` est élargie en conséquence (ex. NCT01313767, NCT03474107, NCT03345342).
- Q2b : fenêtre de tolérance prolongée par une période de suivi (52 semaines de traitement → fin d’étude + 4 semaines) = identique (NCT03700320).
- Q6 : critère conservé, plus le même critère sur une autre fenêtre ou une autre règle de traitement de secours pour une autre agence (FDA, PMDA) = `ajoute` + `delai`, mineur (ex. NCT02278341, NCT01887600).
- Q7 : `ajoute` d’un critère qui n’est pas un nouveau critère d’efficacité (PK, seuil supplémentaire sur une échelle enregistrée, même critère redéposé sous une autre étiquette) = mineur (ex. NCT03735121, NCT01144338).
- Q8 : suppression d’un critère principal de tolérance (absent des secondaires) = `supprime`, majeur, comme toute suppression (ex. NCT02635204, NCT01857622).
