# Intégration des Phases 0, 1 et 2 : analyse du code (25/10/2026)

Branche `integration/phases-0-1-2`, partie de `develop` (socle, mentorat, communauté), avec `feature/accounts` et `feature/courses` de Taha. Analyse menée par lecture du code, exécution des tests, sondes au client de test Django, captures d'écran et Lighthouse.

## 1. Résultat de la fusion

| Étape | Résultat |
|---|---|
| `feature/accounts` (3 commits) | Fusion sans conflit |
| `feature/courses` (18 commits) | Un conflit textuel (`docs/tests.md`) ; changements de Taha dans le socle `core` arbitrés (section 2) |
| Doublon de commande `seed_demo` | La commande de `courses` était masquée par celle de `core` : convertie en `courses/demo.py` (`demo_seeder`) |
| Suite de tests | 318 tests verts après la fusion ; 393 après la correction des bugs (section 4), couverture de 98,4 %, lint et migrations à jour, `check --deploy` sans remarque |
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

## 4. Bugs de la Phase 1 corrigés

Constatés en exécutant le code fusionné, puis corrigés sur la branche d'intégration. Chaque correction a son test de non-régression ; la colonne « Test » donne le fichier.

| Gravité | Bug | Correction | Test |
|---|---|---|---|
| Haute | Visiteur anonyme sur les 4 URL de création du formateur (quiz, question, chapitre, ressource) : **erreur 500** (`TypeError … AnonymousUser`) | Objet parent chargé après le contrôle de rôle, par une `cached_property` | `courses/tests/test_views.py`, `test_permissions.py` |
| Haute | Quiz d'un cours premium ouvert et noté sans abonnement, par URL directe | `QuizDetailView.get_object` applique `can_read_course` ; réponse réservée au rôle apprenant (403 sinon) | `test_views.py` (`PremiumQuizTests`) |
| Haute | Réponse de quiz non numérique : **erreur 500** | Comparaison aux identifiants des choix de la question ; une réponse forgée compte comme fausse | `test_views.py` (`QuizSubmissionTests`) |
| Haute | Deux cours de même titre : **erreur 500** ; renommer un cours cassait ses liens | Slug calculé à la création seulement, avec suffixe s'il est pris (`Course` et `Category`) | `test_models.py`, `test_views.py` |
| Moyenne | Formateur non vérifié : il pouvait publier un cours | Statut « Publié » refusé dans `CourseForm` ; publication de quiz refusée ; avertissement dans « Mes cours » | `test_views.py` (`UnverifiedTrainerTests`) |
| Moyenne | Recruteur sur les URL formateur : 404 au lieu de 403 | Même correction que le premier bug | `test_permissions.py` |
| Moyenne | Le test de la commande d'évaluation supprimait `docs/ia/quiz_generation.md` | Option `--output` ; le test écrit dans un dossier temporaire | `test_commands.py` |
| Moyenne | Un cours intitulé « Nouveau » était inaccessible | Pages du formateur déplacées sous `formateur/` (`formateur/cours/nouveau/`) | `test_views.py` (`CourseUrlTests`) |
| Moyenne | La génération IA pouvait proposer deux choix identiques : `IntegrityError`, job en échec | Schéma pydantic : quatre choix différents, 300 caractères au plus, énoncés distincts ; écriture en une transaction | `test_ai.py` |
| Basse | Le formateur ne pouvait pas ouvrir son propre brouillon, et n'avait pas de liste « Mes cours » | `CourseDetailView` montre le brouillon à son formateur ; vue « Mes cours » dans la navigation | `test_views.py` (`TrainerCourseTests`) |
| Basse | `novalidate` sur 6 formulaires | Retiré : la validation du navigateur s'ajoute à celle du serveur | Lighthouse |
| Basse | N'importe quel rôle pouvait rejoindre un établissement | `JoinInstitutionView` réservée au rôle apprenant ; lien masqué aux autres | `accounts/tests/test_views.py` |
| Basse | Pas de lien « Mot de passe oublié » sur la page de connexion | Lien ajouté | `accounts/tests/test_views.py` |
| Basse | Une vidéo YouTube « watch » ne s'affichait pas dans l'iframe | `Chapter.video_embed_url` (YouTube, Vimeo) ; lien simple pour un autre site | `test_models.py`, `test_views.py` |
| Basse | Avertissement `RemovedInDjango60Warning` à chaque test | `core.forms.https_url_formfield` (`assume_scheme="https"`) dans `ChapterForm` et `ResourceForm` | Suite sans avertissement |

Bugs trouvés pendant la correction, absents de la première analyse :

| Gravité | Bug | Correction | Test |
|---|---|---|---|
| Haute | Page d'ajout d'un cours dans l'admin Django : **erreur 500** (`prepopulated_fields` sur le slug non éditable) | Slug en lecture seule dans l'admin | `courses/tests/test_admin.py` |
| Haute | Deux choix identiques saisis par le formateur : **erreur 500** (contrainte `unique_choice_per_question`) | `QuestionForm.clean` signale le doublon sur le champ | `test_views.py` (`TrainerQuizTests`) |
| Haute | Ordre de chapitre ou de question déjà pris : **erreur 500** (le parent n'étant pas un champ du formulaire, Django ne validait pas la contrainte) | `clean_order` dans `ChapterForm` et `QuestionForm` ; première position libre proposée | `test_views.py` |
| Moyenne | Un formateur ou un recruteur qui « terminait » un chapitre se retrouvait inscrit au cours | `CompleteChapterView` réservée au rôle apprenant ; bouton masqué aux autres | `test_permissions.py`, `test_views.py` |
| Moyenne | Régénérer un quiz publié supprimait ses questions sous les yeux des apprenants | Génération refusée sur un quiz publié ; bouton « Dépublier le quiz » ajouté | `test_views.py` (`TrainerQuizTests`) |
| Moyenne | La progression en % n'apparaissait nulle part (cahier des charges) | Progression et chapitres terminés sur la page du cours | `test_views.py` (`LearnerProgressTests`) |
| Moyenne | Vidéo YouTube intégrée refusée (erreur 153) : Django envoie `Referrer-Policy: same-origin` | `referrerpolicy="strict-origin-when-cross-origin"` sur l'iframe | `test_views.py` (`ChapterVideoTests`), capture |
| Basse | Liens de réinitialisation du mot de passe écrits en dur (`/comptes/...`) | `reverse_lazy` | `accounts/tests/test_views.py` |
| Basse | Inscription possible sans e-mail : la réinitialisation du mot de passe était alors impossible | E-mail obligatoire à l'inscription | `accounts/tests/test_views.py` |
| Basse | « Mes cours » sur mobile (375 px) : la page entière défilait horizontalement, car les textes `visually-hidden` (position absolue) des cellules sortaient de la zone défilante du tableau | `.sf-table-wrapper { position: relative; }`, qui protège aussi les autres tableaux | Mesure par script à 375 px, avant et après |

## 5. Écarts au cahier des charges et à la Definition of Done (Phase 1)

Comblés pendant la correction :

- **CRUD.** Chapitres, ressources, quiz et questions se créent, se modifient et se suppriment depuis l'interface, avec une page de confirmation ; un quiz se publie et se dépublie.
- **Uploads.** `core.validators.validate_upload_size` limite à 5 Mo l'avatar, le logo, l'image d'un cours et les ressources (migrations `accounts` 0003 et `courses` 0003).
- **Tests.** `courses` passe de 21 à 82 tests (couverture de `courses/views.py` : 65 % → 99 %), avec une matrice d'accès ; `accounts` passe de 23 à 32 tests (profil, profil public, établissement, réinitialisation du mot de passe).

Restent à faire par Taha :

- **Évaluation IA.** `evaluate_quiz_generation` porte sur 5 phrases au lieu des 15 chapitres prévus. Elle utilise un autre prompt que la production et ne mesure ni l'ancrage de l'extrait justificatif ni le taux de doublons. La grille humaine (pertinence, exactitude, clarté) manque, et `docs/ia/quiz_generation.md` n'est pas versionné.
- **Prompt.** Une seule phrase, dans le code de la fonctionnalité au lieu de `courses/ai/prompts.py`, sans version.
- **Administration.** La gestion des utilisateurs et des établissements passe par l'admin Django (réservé au rôle administrateur) ; aucune page dédiée dans l'interface.

## 6. Recommandations pour les PR de Taha

- La PR n° 5 (`feature/courses` → `main`) est en conflit et vise `main` : la fermer au profit de la branche d'intégration.
- La PR n° 6 (`feature/accounts` → `main`) est contenue dans la branche d'intégration : la fermer également.
- Taha relit les corrections de la section 4 sur la branche d'intégration pour pouvoir les expliquer au jury, puis reprend l'évaluation IA (section 5).
