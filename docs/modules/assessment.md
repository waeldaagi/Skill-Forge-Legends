# Module assessment

## Périmètre

Le module gère la certification des apprenants : soumission de preuves, évaluation IA, revue humaine obligatoire, émission de certificat vérifiable, et espace recruteur limité aux données publiques.

## Modèles

- Certification : cours, titre, consignes, seuil de réussite, tentatives max, actif.
- Criterion : nom, description, poids (la grille active doit totaliser 100).
- Submission : preuve apprenant + statut de pipeline.
- AIEvaluation : score détaillé, justifications, confiance, fraude suspectée.
- HumanReview : décision finale mentor/formateur.
- Certificate : identifiant public UUID, PDF, révocation.

## Règles métier clés

- Un apprenant soumet uniquement si le cours est terminé.
- Le nombre de tentatives est plafonné par certification.
- La fraude est suspectée si l'IA le signale ou si la similarité TF-IDF dépasse le seuil.
- Un certificat n'est jamais délivré sans revue humaine validée.
- Le recruteur ne voit que les profils publics et certificats non révoqués.

## Endpoints

- /evaluation/catalogue/
- /evaluation/soumissions/
- /evaluation/revues/
- /certificats/verifier/<uuid>/
- /api/certificats/<uuid>/
