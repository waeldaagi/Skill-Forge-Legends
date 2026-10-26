# Intégration de la Phase 3 (Hamdi) : analyse du code (26/10/2026)

Branche `integration/assessment`, partie de `develop`, avec `feature/assessment` de Hamdi (un commit du 26/10 à 09 h 41, 41 fichiers). Analyse menée par lecture du code, exécution des tests, parcours de tout le site sur les données de démo, captures d'écran et Lighthouse.

## 1. Ce que la branche apporte

| Élément du cahier des charges | État |
|---|---|
| Modèles `Certification`, `Criterion`, `Submission`, `AIEvaluation`, `HumanReview`, `Certificate` avec leurs contraintes | Conformes ; grille de critères à 100 % vérifiée par `clean()` |
| CRUD des certifications et des critères par le formateur | Présent |
| Éligibilité (`is_course_completed`), tentatives limitées, suivi en direct de l'évaluation IA | Présents |
| Anti-fraude : similarité TF-IDF (cosinus, scikit-learn) et signal de l'IA | Présent |
| Revue humaine obligatoire avant tout certificat | Présente |
| Certificat PDF (reportlab) avec QR code, page publique de vérification et endpoint JSON | Présents |
| Révocation par l'administrateur | Action de l'admin Django |
| Espace recruteur : recherche sur les profils publics, profil avec certificats vérifiés, contact par e-mail | Présent ; un profil privé donne 404 (testé) |
| `verified_certificates(user)` | Contrat implémenté |
| `evaluate_assessment` : précision, rappel, F1 de la décision, matrice de confusion, erreur absolue moyenne, latences, 40 soumissions | Présent |

## 2. Problèmes corrigés pendant l'intégration

| Problème | Correction | Test |
|---|---|---|
| Deux migrations `courses/0004` : Django refusait de migrer | Celle de Hamdi devient la 0005 ; elle n'utilise que `get_or_create` | `makemigrations --check` |
| Objets chargés avant le contrôle de rôle : erreur 500 pour un anonyme sur les critères et la revue, 404 au lieu de la connexion sur la soumission et le contact, 404 au lieu de 403 pour un autre rôle | `cached_property` après le contrôle de rôle | `core/tests/test_url_protection.py`, `assessment/tests/test_rules.py` |
| Une soumission déjà décidée pouvait être relue : passer de « Réussie » à « Échouée » laissait le certificat délivré | Revue limitée aux statuts en attente | `test_rules.py` |
| Le relecteur ne voyait ni la preuve ni le détail de l'IA | Preuve, scores par critère et fraude suspectée sur la page de revue ; score de l'IA proposé par défaut | `test_rules.py` |
| L'anti-plagiat comparait aussi les tentatives du même apprenant : retenter avec un texte amélioré passait pour une copie | Tentatives du même apprenant exclues | `test_rules.py` |
| QR code du certificat en URL relative : inutilisable une fois scanné | URL absolue de la page de vérification | `test_rules.py` |
| Formulaire de certification : cours de tous les formateurs proposés ; un formateur non vérifié pouvait l'activer | Cours du formateur seulement ; activation refusée sans vérification | `test_rules.py` |
| Lien « Talents certifiés » au menu de l'administrateur, vers une page réservée au recruteur (403) | Lien retiré | `test_site_crawl.py` |
| Menu de l'apprenant, du mentor et du formateur sur deux lignes avec les nouveaux liens | Libellés raccourcis (« Cours », « Mentors », « Revues ») | Mesure à 1200 px |
| L'apprenant ne voyait pas la décision ni le commentaire du mentor | Décision, score final et commentaire sur le détail de la soumission | `test_rules.py` |
| Aucune donnée de démo : impossible de montrer une certification sans tout saisir | `assessment/demo.py` : certification du cours Django, certificat de Yasmine, soumission de Rania en attente, profil public | `assessment/tests/test_demo.py` |
| Tests du catalogue de cours cassés par les catégories créées par migration | Tests adaptés | Suite verte |

`assessment` passe de 20 à 39 tests (couverture de 92 %).

## 3. Écarts restant (à faire par Hamdi)

- **Métriques de l'IA.** `docs/ia/assessment.md` publie des résultats obtenus avec le fournisseur `mock`, qui ne dit rien de l'IA réelle. Il faut relancer `evaluate_assessment --provider gemini` et commenter les erreurs, comme dans `docs/ia/moderation.md`.
- **Score de l'IA.** Le score total vient de l'IA sans être recalculé à partir des poids de la grille, et les noms de critères renvoyés ne sont pas comparés à ceux de la grille.
- **Interface du formateur** : la liste des certifications, les formulaires de critères et les confirmations de suppression gardent une mise en page minimale.

## 4. Vérifications

- 487 tests verts, couverture totale de 97,0 %, lint et migrations à jour.
- Parcours de tout le site sur les données de démo, pour les six rôles et l'anonyme : aucune erreur 500, aucun lien cassé ou interdit ; 219 pages contrôlées à 375 px sans anomalie (hors du style que Chart.js pose sur son `<canvas>`).
- Lighthouse (accessibilité) : 100 sur les 12 pages de la Phase 3, dont la page publique de vérification d'un certificat.
- Menu sur une ligne pour les six rôles à 1200 px.
