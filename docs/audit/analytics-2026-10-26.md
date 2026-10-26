# Intégration de la Phase 4 (Ismail) : analyse du code (26/10/2026)

Branche `integration/analytics`, partie de `develop`, avec `feature/analytics` d'Ismail (un commit du 26/10 à 00 h 04). Analyse menée par lecture du code, exécution des tests, captures d'écran et Lighthouse.

## 1. Ce que la branche apporte

| Élément | État |
|---|---|
| Jeu de données synthétique (`generate_dropout_dataset`, 200 lignes, graine fixe) | Conforme, documenté comme synthétique |
| `train_dropout_model` : régression logistique et forêt aléatoire, découpage stratifié, précision, rappel, F1, matrice de confusion, ROC-AUC, modèle sauvegardé avec joblib | Conforme. Régression logistique retenue : F1 de 0,75, ROC-AUC de 0,88 sur 50 exemples de test |
| Page « Pilotage » (indicateurs du compte, graphique Chart.js, tableau de valeurs) et export CSV | Présente |
| Page « Analytics IA » : résumé du modèle, latence moyenne et p95, taux d'échec des appels IA par fonctionnalité (`AICallLog`) | Présente |

## 2. Problèmes corrigés pendant l'intégration

| Problème | Correction |
|---|---|
| Six fichiers refusés par `ruff format` : la CI aurait échoué | Mise en forme appliquée |
| Migration `payments` 0002 (renommage de l'index) en conflit avec le nom d'index fixé dans le modèle sur `main` | Migration d'Ismail conservée ; le modèle reprend le nom calculé par Django |
| Liens « Pilotage » et « Analytics IA » ajoutés au menu des six rôles : menu de l'apprenant sur deux lignes, statistiques techniques proposées à tous | « Analytics IA » réservé à l'administrateur (403 sinon) ; « Pilotage » au menu de l'établissement et de l'administrateur ; l'apprenant y accède par un panneau « Mes indicateurs » de son tableau de bord |
| Les deux pages ouvraient un second `<main id="contenu">` | Gabarits repris avec les classes du thème |
| Chart.js chargé depuis un CDN, avec un script en ligne | Fichier local `static/vendor/chartjs/`, script `analytics/static/analytics/pilotage.js`, hauteur fixe, mouvement réduit respecté |
| Progression, certificats et sessions de mentorat affichés à 0 en dur | Valeurs réelles, lues en lecture seule dans `courses`, `assessment` et `mentoring` |
| Export CSV : identifiants anglais et dictionnaire brut dans une cellule | Libellés français ; une ligne par fonctionnalité IA |
| Scénario « paiement refusé » prévu par la vue mais sans bouton | Bouton « Simuler un paiement refusé » sur la page des offres |
| Conflit dans `plan_list.html` | Version de `develop`, qui contenait déjà les liens ajoutés |

Tests ajoutés : accès réservé, menus par rôle, vrais indicateurs, export CSV, scénario refusé, commandes de génération et d'entraînement dans un dossier temporaire. `analytics` passe de 10 à 16 tests (couverture de 94 %), `payments` de 18 à 20.

## 3. Écarts restant au cahier des charges (Phase 4, à faire par Ismail)

- **Tableaux de bord par rôle.** Le formateur (inscrits, taux de complétion, score moyen aux quiz par cours) et le mentor (sessions, note moyenne) n'ont pas de vue dédiée ; « Pilotage » montre les mêmes indicateurs, centrés sur les paiements, à tous les rôles.
- **Risque d'abandon dans l'espace établissement.** Le modèle est entraîné mais jamais appliqué : l'établissement ne voit ni ses apprenants ni leur risque (faible, moyen, élevé).
- **Recalcul par une tâche Celery**, avec bouton et indicateur de chargement, et temps d'inférence mesuré : absents.
- **Administrateur** : utilisateurs par rôle, sessions, certificats et modération manquent à la vue administrateur.
- **Rapport `docs/ia/dropout.md`** : les chiffres y sont, sans lecture des erreurs ni limites (50 exemples de test, 4 abandons seulement ; F1 instable sur si peu de cas positifs).
- **Fiches de module** : `docs/modules/payments.md` et `docs/modules/analytics.md` n'existent pas.
- **Matrice d'accès** : pas de `test_permissions.py` dans `payments` ni `analytics` ; l'accès anonyme est couvert par `core/tests/test_url_protection.py`.

## 4. Vérifications

- 448 tests verts, couverture totale de 98,1 %, lint et migrations à jour.
- Menu sur une ligne pour les six rôles, à 1200 et 1280 px.
- Lighthouse (accessibilité) : 100 sur « Pilotage » (apprenante, établissement, administratrice), « Analytics IA » et le tableau de bord de l'apprenante.
- Contrôle automatique des pages (203 pages, six rôles et l'anonyme) : aucune anomalie, hors du style que Chart.js pose sur son `<canvas>` à l'exécution.
