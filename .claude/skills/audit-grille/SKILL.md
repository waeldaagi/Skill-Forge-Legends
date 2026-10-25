---
name: audit-grille
description: Audit d'un module SkillForge ou du projet entier contre la grille de validation ESPRIT 5TWIN (CRUD, tests et BNF, accessibilité, IA, UX/UI, Git, intégration et déploiement), avec preuves et liste de corrections priorisées. À charger quand on demande un audit, « est-ce prêt pour la validation », « où en est mon module », ou avant une démo.
---

# Audit contre la grille de validation

Tu joues le jury, avec la grille en main. Tu ne corriges rien pendant l'audit : tu constates, tu prouves, tu priorises. Les corrections viennent après, seulement si l'utilisateur les demande.

## 1. La grille (résumé fidèle)

Si `docs/references/` contient la grille officielle, elle fait foi. Sinon, utilise ce résumé.

| Critère | Points | Sous-critères |
|---|---|---|
| Fonctionnalités & CRUD | 2 | Opérations de base (1) ; cohérence avec le cahier des charges, aucune fonctionnalité cassée en démo (1) |
| Tests | 2 | Unitaires modèles/logique (0,75) ; intégration vues/statuts HTTP (0,75) ; rapport coverage.py et exécution sans erreur (0,5) |
| BNF | 2 | Sécurité OWASP Django (0,75) ; rôles et permissions sans contournement par URL (0,75) ; robustesse, pages 404/500, validation des entrées (0,5) |
| Accessibilité | 2 | Sémantique HTML (0,5) ; ARIA et `alt` (0,5) ; contraste WCAG AA (0,5) ; navigation clavier et focus visible (0,5) |
| IA | 4 | Pertinence (0,75) ; intégration propre, clé en variable d'environnement (0,75) ; retour utilisateur pendant/après l'appel (0,5) ; métriques chiffrées (1) ; temps de réponse mesuré et asynchronisme Celery/Redis (1) |
| UX/UI | 1 | Interface claire, responsive, cohérente |
| Q/R et QCM | 8 | Maîtrise individuelle, justification des choix |

Niveaux de la grille :
- CRUD : Insuffisant 0–0,5 (une opération ne marche pas ou plantage) ; Satisfaisant 1–1,5 ; Excellent 2 (fluide, validations serveur et client, aucun bug).
- Tests & BNF : Insuffisant 0–1 ; Satisfaisant 1,5–2,5 ; Excellent 3–4 (tests structurés, couverture démontrée, permissions testées explicitement, sécurité justifiée à l'oral).
- Accessibilité : Excellent = audit Lighthouse/axe démontré, contrastes conformes, clavier fluide.
- IA : Excellent 3–4 = cas pertinent, métriques chiffrées **et commentées**, asynchronisme démontré.

Règles éliminatoires : pas de Git → note individuelle / 2 ; pas d'intégration et de déploiement → note d'équipe = 0.

Remarque : le tableau récapitulatif officiel donne 3 points à « Tests & BNF » alors que le détail en compte 4 (total 21). Signale-le dans le rapport comme point à clarifier avec l'enseignant.

## 2. Collecte des preuves

Périmètre : une app (`<app>`) ou `tout`. Lance ce qui s'applique et garde les sorties.

```
python manage.py test <app> --verbosity 1
coverage run manage.py test <app> && coverage report --include="<app>/*"
ruff check <app>
python manage.py makemigrations --check --dry-run
python manage.py check --deploy --settings=config.settings.prod
git grep -nE "\.raw\(|cursor\(\)|csrf_exempt|DEBUG *= *True|SECRET_KEY *= *['\"]" -- <app> config
git shortlog -sn -- <app>/
git log --oneline -- <app>/ | head -20
```

Puis lis le code :
- `urls.py` et `views.py` : chaque vue protégée a-t-elle un contrôle d'accès ? Chaque vue de détail ou de modification filtre-t-elle sur le propriétaire ?
- Templates : `grep` des `<img` sans `alt`, des pages avec plusieurs `<h1>`, des champs sans `<label>`, des `onclick` sur `div` ou `span`, des styles en ligne.
- Contraste : compare les couleurs utilisées au tableau de `docs/accessibilite.md`.
- IA : existence de la tâche Celery, de l'usage d'`AIJob`, du statut en direct, du repli, de la commande `evaluate_*`, de `docs/ia/<feature>.md` **avec de vrais chiffres**.
- Pour l'affichage, rends les pages principales avec le client de test Django pour chaque rôle et inspecte le HTML (repères, titres, libellés).

## 3. Rapport

Écris `docs/audit/<app>-<AAAA-MM-JJ>.md` :

1. **Synthèse** : note estimée par critère, niveau de la grille (Insuffisant / Satisfaisant / Excellent), et les 3 risques principaux.
2. **Tableau par sous-critère** : points max, estimation, preuve (fichier:ligne ou sortie de commande), manque.
3. **Corrections priorisées** : impact sur la note ÷ effort, les 5 premières en tête, chacune avec les fichiers à toucher.
4. **Questions que le jury posera sur les faiblesses**, avec une réponse honnête préparée.
5. **Contrôles éliminatoires** : commits de chaque membre sur ses apps, état de l'intégration (`develop`/`main`), URL de déploiement.

## 4. Règles

- Estime avec sévérité : en cas de doute entre deux niveaux, prends le plus bas.
- Chaque affirmation repose sur une preuve. Pas de preuve, pas de point.
- Ne compte pas une fonctionnalité qui n'est pas accessible depuis l'interface.
- Ne modifie aucun fichier hors de `docs/audit/` pendant l'audit.
