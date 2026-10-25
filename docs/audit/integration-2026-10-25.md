# Intégration des Phases 0, 1 et 2 : analyse du code (25/10/2026)

Branche `integration/phases-0-1-2`, partie de `develop` (socle, mentorat, communauté), avec `feature/accounts` et `feature/courses` de Taha. Analyse menée par lecture du code, exécution des tests, sondes au client de test Django, captures d'écran et Lighthouse.

## 1. Résultat de la fusion

| Étape | Résultat |
|---|---|
| `feature/accounts` (3 commits) | Fusion sans conflit |
| `feature/courses` (18 commits) | Un conflit textuel (`docs/tests.md`) ; changements de Taha dans le socle `core` arbitrés (section 2) |
| Doublon de commande `seed_demo` | La commande de `courses` était masquée par celle de `core` : convertie en `courses/demo.py` (`demo_seeder`) |
| Suite de tests | 318 tests verts, lint et migrations à jour, `check --deploy` sans remarque |
| `seed_demo` | Crée les comptes, le cours Django, puis le mentorat et le forum qui s'y rattachent |

## 2. Arbitrages sur le socle `core`

| Changement de Taha | Décision | Raison |
|---|---|---|
| Message clair sur un 404 de Gemini (`core/ai/client.py`) | Conservé | Aide à diagnostiquer un `AI_MODEL` erroné |
| Relances après 5 s puis 10 s (`core/ai/jobs.py`) | Conservé | Les 503 de Gemini durent quelques secondes |
| Délai global `AI_TIMEOUT`, qui ignorait le paramètre `timeout` | Non repris | La génération de quiz passe `timeout=60` à `complete_json` ; les autres fonctionnalités gardent 30 s |
| Modèle par défaut `gemini-2.5-flash` | Non repris | Réglable dans `.env` par `AI_MODEL` |
| `NoReverseMatch` ignorée dans la navigation | Non repris | Un lien mal nommé doit produire une erreur visible, pas disparaître |
| Mention « après avoir révoqué la clé exposée » dans `.env.example` | Retirée | Aucune clé n'apparaît dans l'historique Git ni dans les PR (vérifié) ; si une clé a été exposée ailleurs, Taha doit confirmer qu'elle est révoquée |

## 3. Corrections faites pendant l'intégration

| Problème | Preuve | Commit |
|---|---|---|
| L'administrateur voyait deux fois « Administration » dans le menu | Sonde : `['Administration', 'Administration', …]` | `fix(accounts): retire le lien Administration en double` |
| `is_verified`, compétences, établissement absents de l'admin : aucun mentor ni formateur ne pouvait être vérifié | Lecture de `accounts/admin.py` | `fix(accounts): expose la vérification et le profil` |
| 15 gabarits utilisent `sf-btn-primary`, classe définie nulle part : boutons affichés comme du texte | Capture et style calculé (fond transparent) | `fix(core): garde l'en-tête sur une ligne et style les boutons` |
| Menu sur deux lignes à 1280 px après l'ajout des liens de la Phase 1 | Capture | même commit, et `fix(accounts): retire le lien Mon profil` |
| Bouton `btn-outline-secondary` à 4,48:1 sur le fond de page | Lighthouse : 95/100 sur le profil et la gestion de quiz | `fix(core): porte le bouton contour secondaire au contraste AA` |

Ajouts de la feuille de route rendus possibles par la Phase 1 : expertises des mentors, cours concerné par une session, mentors vérifiés (mentorat) ; cours et tags des sujets (communauté).

## 4. Bugs restant dans le code de la Phase 1 (à corriger par Taha)

Constatés en exécutant le code fusionné. Non corrigés ici pour que Taha garde la maîtrise de ses modules et puisse les expliquer au jury.

| Gravité | Bug | Preuve | Correction proposée |
|---|---|---|---|
| Haute | Visiteur anonyme sur les 4 URL de création du formateur (quiz, question, chapitre, ressource) : **erreur 500** | `TypeError: Field 'id' expected a number but got AnonymousUser` | `courses/views.py:150, 185, 337, 365` : charger l'objet après le contrôle de rôle (`cached_property` utilisée dans `get_context_data` et `form_valid`), comme dans `mentoring/views.py` |
| Haute | Quiz d'un cours premium ouvert et noté sans abonnement, par URL directe (le chapitre, lui, est protégé) | Sonde : GET 200, POST 302 avec `has_active_subscription` à `False` | `QuizDetailView` (`courses/views.py:102`) : refuser si `user_can_access_course` est faux, et réserver la soumission au rôle apprenant |
| Haute | Réponse de quiz non numérique : **erreur 500** | `ValueError: Field 'id' expected a number but got 'abc'` | `courses/views.py:118` : comparer aux identifiants des choix déjà chargés (`{choice.pk for choice in question.choices.all()}`) au lieu de filtrer avec la valeur brute |
| Haute | Deux cours de même titre : **erreur 500** ; renommer un cours casse ses liens | `IntegrityError: UNIQUE constraint failed: courses_course.slug` | `courses/models.py:69` (et `:22` pour `Category`) : calculer le slug à la création seulement, avec un suffixe si déjà pris, et valider l'unicité dans le formulaire |
| Moyenne | Formateur non vérifié : il peut publier un cours (contraire au cahier des charges) | Sonde : cours publié créé | `TrainerCourseCreateView` et la publication des quiz : refuser si `request.user.is_verified` est faux |
| Moyenne | Recruteur sur les URL formateur : 404 au lieu de 403 | Sonde | Même correction que le premier bug |
| Moyenne | Le test de la commande d'évaluation **supprime `docs/ia/quiz_generation.md`** | `courses/tests/test_commands.py:25` | Écrire le rapport dans un dossier temporaire (option `--output`) |
| Moyenne | Un cours intitulé « Nouveau » est inaccessible (son URL est celle de la création) | Sonde : `/cours/nouveau/` ouvre la création | Préfixer la création (`formateur/cours/nouveau/`) ou réserver ce slug |
| Moyenne | La génération IA peut proposer deux choix identiques : la contrainte d'unicité lève une erreur, le job échoue | Lecture : aucune validation d'unicité dans `GeneratedQuestion` | Valider l'unicité des 4 choix dans le schéma pydantic : la sortie sera redemandée une fois |
| Basse | Le formateur ne peut pas ouvrir son propre cours en brouillon, et n'a pas de liste « Mes cours » | Sonde : 404 sur son brouillon | Vue « Mes cours » et aperçu du brouillon pour son formateur |
| Basse | `novalidate` sur 6 formulaires : validation du navigateur désactivée | Lecture des gabarits | Retirer `novalidate` |
| Basse | N'importe quel rôle peut rejoindre un établissement | `accounts/views.py:55` | Réserver au rôle apprenant |
| Basse | Pas de lien « Mot de passe oublié » sur la page de connexion | Lecture de `login.html` | Ajouter le lien vers `accounts:password_reset` |
| Basse | Une vidéo YouTube collée en URL « watch » ne s'affiche pas dans l'iframe du chapitre | Lecture de `chapter.html` | Convertir l'URL en URL d'intégration, ou afficher un lien |
| Basse | Avertissement `RemovedInDjango60Warning` à chaque test : champs URL des formulaires sans protocole par défaut | Sortie de pytest | Dans `ChapterForm` et `ResourceForm`, déclarer les champs URL avec `forms.URLField(assume_scheme="https")` |

## 5. Écarts au cahier des charges et à la Definition of Done (Phase 1)

- **CRUD incomplet.** Chapitres et ressources : création seulement. Quiz et questions : pas de suppression. Administrateur : pas de gestion des utilisateurs ni des établissements dans l'interface (seulement dans l'admin Django).
- **Uploads.** Extensions vérifiées, mais aucune limite de 5 Mo (avatar, logo, image de cours, ressources).
- **Tests.** 21 tests pour `courses` ; 2 tests ajoutés pour `accounts` (inscription), aucun pour le profil, le profil public ou l'adhésion à un établissement. `courses/views.py` n'est couvert qu'à 65 % : les bugs de la section 4 sont précisément dans les parties non testées. Aucune matrice d'accès.
- **Évaluation IA.** `evaluate_quiz_generation` porte sur 5 phrases au lieu des 15 chapitres prévus. Elle utilise un autre prompt que la production et ne mesure ni l'ancrage de l'extrait justificatif ni le taux de doublons. La grille humaine (pertinence, exactitude, clarté) manque.
- **Prompt.** Une seule phrase, dans le code de la fonctionnalité au lieu de `courses/ai/prompts.py`, sans version.

## 6. Recommandations pour les PR de Taha

- La PR n° 5 (`feature/courses` → `main`) est en conflit et vise `main` : la fermer au profit de la branche d'intégration, ou la recibler vers `develop`.
- La PR n° 6 (`feature/accounts` → `main`) se fusionne sans conflit, mais elle aussi devrait viser `develop`.
- Corriger d'abord les quatre bugs de gravité haute, avec un test chacun ; puis compléter le CRUD et la matrice d'accès de `courses`.
