# CLAUDE.md : SkillForge

Plateforme d'e-learning Django : cours, mentorat en direct, certification évaluée par l'IA puis validée par un mentor. Promesse : Apprendre → Être accompagné → Prouver → Partager. Projet académique ESPRIT, classe 5TWIN, équipe de 4. Le plan complet par phase est dans `PROMPT_CLAUDE_CODE_SKILLFORGE.md` : ce fichier est transmis à chaque membre et n'est jamais versionné.

## Apps et responsables

| App | Module | Responsable |
|---|---|---|
| `core` | Socle : gabarits, permissions, service IA, erreurs | Wael Daagi |
| `accounts` | Comptes et rôles | Taha Liouane |
| `courses` | Catalogue et cours | Taha Liouane |
| `mentoring` | Mentorat en direct | Wael Daagi |
| `community` | Communauté (forum, entraide) | Wael Daagi |
| `assessment` | Évaluation et preuve, espace recruteur | Hamdi Ben Rayana |
| `payments` | Paiements et offres | Ismail Belhoula |
| `analytics` | Pilotage et analytics (lecture seule des autres apps) | Ismail Belhoula |

Rôles (`accounts.User.Role`) : `APPRENANT`, `MENTOR`, `FORMATEUR`, `RECRUTEUR`, `ADMIN`, `ETABLISSEMENT`.

## Stack

Python 3.12 (virtualenv), Django 5.2 LTS (`Django==5.2.18`), PostgreSQL 16 via Docker (SQLite si `DATABASE_URL` est absent), Celery + Redis, templates Django + Bootstrap 5.3 + HTMX 2 + Chart.js en fichiers locaux (`static/vendor/`, aucun CDN), django-environ, whitenoise, gunicorn, Pillow, reportlab + qrcode, scikit-learn + joblib, pydantic, httpx. Dev : pytest, pytest-django, pytest-cov, coverage, factory-boy, ruff. Visio : Jitsi Meet en iframe. Paiement : passerelle simulée, aucune donnée de carte. Pas de DRF, pas de SPA : quelques `JsonResponse` suffisent.

Settings : `config/settings/{base,dev,test,prod}.py`. `manage.py` utilise `dev`, sauf `manage.py test` qui utilise `test` (comme pytest). `wsgi.py` et `asgi.py` utilisent `prod`.

## Règles de travail

1. Une phase à la fois. Au début, afficher un plan court (modèles, URLs, fichiers), puis exécuter.
2. Commits petits et fréquents, en français : `type(app): verbe au présent + objet`, 72 caractères au maximum.
3. Branches `feature/<app>` créées depuis `develop`.
4. Jamais de `git push` sans accord. Ne jamais modifier `user.name` ni `user.email` de Git.
5. Ne pas modifier l'app d'un autre responsable, sauf les contrats ci-dessous. Si c'est nécessaire, le signaler.
6. Après chaque fonctionnalité : `ruff check .`, `ruff format --check .`, `python manage.py makemigrations --check`, tests verts.
7. Aucun secret dans le code ni dans l'historique. `.env` est ignoré par Git ; `.env.example` reste à jour.
8. Code en anglais ; interface et documentation en français. `LANGUAGE_CODE = "fr-fr"`, `TIME_ZONE = "Africa/Tunis"`.
9. Logique métier dans `services.py`, tâches dans `tasks.py`, vues fines (CBV de préférence).
10. Demander avant toute action ambiguë ou irréversible : suppression de données, déploiement, réécriture d'historique.

Skills du projet (`.claude/skills/`), à charger **avant** d'écrire :

| Skill | Quand |
|---|---|
| `django-craft` | Tout code Python/Django ; relecture du diff avant chaque commit |
| `ui-identity` | Templates, CSS, textes affichés |
| `redaction-fr` | README, `docs/`, rapports IA, messages de commit |
| `tests-utiles` | Écriture et relecture des tests |
| `audit-grille` | Fin de chaque phase : audit du module contre la grille |
| `prep-soutenance` | Révision avec l'étudiant responsable, sur demande |

## Conventions posées par le socle (Phase 0)

- **Permissions par rôle** : chaque app déclare dans son `AppConfig` un attribut `role_permissions = {"MENTOR": ["mentoring.add_availabilityslot", ...]}`. `python manage.py setup_roles` agrège ces déclarations, crée un groupe par rôle (nommé comme la valeur du rôle) et lui attribue ces permissions. La commande peut être relancée sans risque.
- **Groupes** : un utilisateur rejoint le groupe de son rôle à sa création et en change quand son rôle change (`accounts.User.save`). Le rôle `ADMIN` donne `is_staff`. Les groupes ne s'éditent pas à la main dans l'admin.
- **Navigation** : chaque app déclare dans son `AppConfig` un attribut `role_navigation = {"MENTOR": [("Mes créneaux", "mentoring:slot_list")]}`. Le context processor `core.context_processors.navigation` construit le menu.
- **Contrôle d'accès** (`core.permissions`) :
  - `RoleRequiredMixin` avec `allowed_roles` : un anonyme est redirigé vers la connexion, un rôle non autorisé reçoit 403 ;
  - `role_required(*roles)` : même règle pour une vue fonction ;
  - `OwnerRequiredMixin` avec `owner_field` : filtre le queryset, l'objet d'autrui donne 404.
- **Formulaires** : `FORM_RENDERER = "core.forms.SkillForgeFormRenderer"`. `{{ form }}` produit les libellés, les classes Bootstrap, la mention « (obligatoire) », `aria-invalid` et `aria-describedby`. Aucune classe CSS n'est à poser dans les formulaires.
- **Champs URL et fichiers** : un ModelForm avec un `URLField` déclare `formfield_callback = https_url_formfield` (`core.forms`) dans sa `Meta` : une URL sans protocole devient `https://`, comme dans Django 6.0. Tout `FileField` ou `ImageField` porte `core.validators.validate_upload_size` (5 Mo) en plus de `FileExtensionValidator`.
- **E-mails** : `core.services.queue_email(subject, message, recipient_list)`. L'e-mail est confié à Celery après la validation de la transaction. Pour un envoi différé (rappel 1 h avant), utiliser `core.tasks.send_email.apply_async(..., eta=...)`.
- **Erreurs** : gabarits `templates/403.html`, `404.html`, `500.html`, `403_csrf.html`. Le message d'une `PermissionDenied` s'affiche sur la page 403 : il doit être rédigé pour l'utilisateur.
- **Profils vérifiés** : un mentor ou un formateur non vérifié (`User.is_verified`, coché par un administrateur dans l'admin) ne publie rien. Mentorat : `mentoring.services.ensure_can_publish`, annuaire et réservation filtrés. Cours : `CourseForm` refuse le statut « Publié » et `PublishQuizView` la publication d'un quiz (`courses.services.UNVERIFIED_TRAINER_MESSAGE`).
- **Gabarits** : hériter de `base.html`, un seul `<h1>`, aucun style en ligne, classes et jetons de `static/css/theme.css` (`sf-page-header`, `sf-filters`, `sf-cards`, `sf-details`, `sf-actions`, `sf-status--<statut>`). Listes paginées : `{% include "core/partials/pagination.html" %}`, qui conserve les filtres. Une liste `annotate(Count(...))` a besoin d'un `order_by` explicite : une requête agrégée ignore `Meta.ordering`.
- **Données de démo** : chaque app déclare dans son `AppConfig` un attribut `demo_seeder = "<app>.demo.seed"`. `seed(accounts)` reçoit les comptes de démo par rôle, crée ses données sans dupliquer (`get_or_create`) et renvoie un résumé d'une ligne. Comptes secondaires : `core.demo.create_demo_user`. Jamais d'appel à l'IA dans un seed.

## Socle IA (`core/ai/`)

Toutes les fonctionnalités IA passent par ce socle.

- `complete_json(feature, system, prompt, schema, timeout=30, provider_name=None)` renvoie une instance pydantic validée. Le client ajoute au prompt système la consigne anti-injection et le schéma JSON. Une réponse invalide est redemandée une fois, avec les erreurs de validation. Un timeout, une erreur HTTP ou un service injoignable lèvent `AIServiceError` (`error_type`, `user_message`, `retryable`).
- Fournisseurs : `core/ai/providers/`. `mock` est déterministe et sert aux tests, à la CI et à la démo hors ligne. Le fournisseur réel est `gemini` (API `generateContent` en REST, sortie JSON imposée, modèle par défaut `gemini-3.5-flash-lite`). Configuration `.env` : `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`.
- Journal : chaque appel crée un `AICallLog` (fonctionnalité, fournisseur, modèle, `duration_ms`, succès, type d'erreur, date), sans aucune donnée personnelle.
- `run_ai_job(feature, user, target=None, payload=None)` crée un `AIJob` (`PENDING` → `RUNNING` → `SUCCEEDED`/`FAILED`) et lance la tâche Celery après la validation de la transaction. Une erreur passagère (timeout, 429, 5xx, réseau) est relancée deux fois, avec un backoff de 2 s puis 4 s. Après l'échec final : `FAILED`, message en français, puis repli métier.
- Statut en direct dans un template : `{% load ai_status %}{% ai_job_status job %}`. Cette balise affiche une zone `role="status"` qui interroge `core:ai_job_status` toutes les 2 s. La vue est réservée au propriétaire et répond 286 quand le job est terminé, ce qui arrête le polling.
- Prompts versionnés dans `<app>/ai/prompts.py`. Le texte de l'utilisateur passe par `delimit_user_content(text)`. La sortie est toujours validée par un schéma pydantic.
- Évaluation : une commande `evaluate_<feature>` par fonctionnalité, avec `--provider`, des métriques `sklearn.metrics`, les latences moyenne, médiane et p95, et les résultats dans `docs/ia/<feature>.md`.
- Jeux de données : 40 à 100 exemples étiquetés en fixtures JSON. L'étudiant relit et corrige les étiquettes.

Brancher une fonctionnalité IA dans un module :

```python
# community/apps.py
class CommunityConfig(AppConfig):
    name = "community"

    def ready(self):
        from core.ai import AIFeature, register_feature
        from .ai import moderation

        register_feature(
            AIFeature(
                name="moderation",
                status_message="Vérification de votre message en cours…",
                failure_message="Un modérateur relira votre message avant publication.",
                run=moderation.run,  # run(job) -> dict : complete_json + mise à jour de job.target
                fallback=moderation.fallback,  # fallback(job) : repli métier (file humaine)
                mock_output=moderation.mock_output,  # mock_output(prompt) -> dict valide pour le schéma
            )
        )
```

Dans les tests, `run_ai_job` n'exécute la tâche qu'à la validation de la transaction. Il faut donc l'entourer de `with self.captureOnCommitCallbacks(execute=True):`. Pour un service qui envoie un e-mail via `queue_email`, même règle.

## Accessibilité et charte

- `<html lang="fr">`, lien d'évitement, repères `header` / `nav aria-label="Navigation principale"` / `main id="contenu"` / `footer`, un seul `<h1>` sans saut de niveau.
- Champs : `<label for>`, erreurs liées par `aria-describedby`, `aria-invalid="true"`, obligatoire écrit en texte (fourni par le renderer).
- Boutons-icônes avec `aria-label` ; images avec `alt` (vide si décoratives) ; iframe Jitsi avec `title`.
- Statut IA et messages : `aria-live="polite"` ou `role="status"` ; alertes : `role="alert"`.
- Clavier : tout est atteignable avec Tab et Entrée, aucun `div` cliquable, focus visible de 3 px, modales fermées par Échap.
- Graphiques Chart.js : `role="img"`, `aria-label`, tableau de données dans un `<details>`.
- Jetons : `--sf-navy #0B1026`, `--sf-violet #6D28D9`, `--sf-orange #F97316`, `--sf-text #1F2937`, `--sf-bg #F8FAFC`. Orange jamais en texte sur fond clair ; bouton orange (`.btn-accent`) avec texte bleu nuit.
- Toute nouvelle paire texte/fond est vérifiée (≥ 4,5:1) et ajoutée à `docs/accessibilite.md`. Mobile d'abord ; `prefers-reduced-motion` respecté.

## Contrats entre modules

| Contrat | Signature | État |
|---|---|---|
| `core.permissions` | `RoleRequiredMixin`, `role_required`, `OwnerRequiredMixin` | Implémenté |
| `courses.services` | `user_can_access_course(user, course) -> bool`, `can_read_course(user, course) -> bool` (le formateur relit son propre cours), `course_progress(user, course) -> int` (0 à 100), `is_course_completed(user, course) -> bool`, `enroll_learner(user, course)` | Implémenté (Phase 1) |
| `payments.services` | `has_active_subscription(user) -> bool` | Stub (`True`) jusqu'à la Phase 4 |
| `assessment.services` | `verified_certificates(user)` : certificats non révoqués | Stub (liste vide) jusqu'à la Phase 3 |
| `core.ai` | `run_ai_job(...) -> AIJob`, `complete_json(...)` | Implémenté |

`analytics` lit les autres apps en lecture seule (services et requêtes ORM) et n'y écrit jamais.

## Definition of Done (chaque module)

- Modèles avec contraintes (`unique`, `UniqueConstraint`, `CheckConstraint`, validators) et `__str__`.
- `admin.py` configuré (`list_display`, filtres, recherche).
- CRUD complet via l'interface, pas seulement l'admin.
- ModelForms avec `clean()`, attributs HTML5, messages Django.
- Listes paginées avec recherche et filtres.
- Accès : `RoleRequiredMixin` (qui inclut la connexion) et contrôle de propriété ; l'objet d'autrui donne 403 ou 404.
- Uploads validés : extensions en liste blanche, 5 Mo au maximum.
- Fonctionnalité IA : tâche Celery, `AIJob`, statut en direct, message d'erreur, repli, commande d'évaluation, `docs/ia/<feature>.md`.
- Gabarits conformes à la section accessibilité.
- Tests : modèles, services, formulaires ; vues (statut, template, contexte) ; permissions (autorisé et refusé par rôle, objet d'autrui) ; tâche IA avec `mock`.
- Données de démo dans `seed_demo`.
- `docs/modules/<app>.md` rédigé.

## Commandes de référence

```
python manage.py migrate
python manage.py setup_roles
python manage.py seed_demo                      # exige DEMO_PASSWORD dans .env
python manage.py runserver
celery -A config worker -l info --pool=solo     # --pool=solo sous Windows
celery -A config beat -l info
python manage.py test                           # ou : pytest
coverage run manage.py test && coverage report && coverage html
ruff check . && ruff format --check .
python manage.py makemigrations --check --dry-run
python manage.py evaluate_<feature> --provider <réel>
python manage.py check --deploy --settings=config.settings.prod   # exige ALLOWED_HOSTS
docker compose up -d                            # PostgreSQL 16 et Redis 7
```

## Pièges connus

- `config.settings.prod` exige `SECRET_KEY` et `ALLOWED_HOSTS` dans l'environnement.
- Fichiers JS/CSS tiers ajoutés dans `static/vendor/` : retirer la ligne `sourceMappingURL` si le fichier `.map` n'est pas fourni, sinon `collectstatic` échoue avec le stockage manifeste.
- `.gitattributes` impose LF dans le dépôt : le futur script d'entrée Docker en dépend.
- Sous Windows, écrire `127.0.0.1` et non `localhost` dans `DATABASE_URL` et `REDIS_URL` : `localhost` est d'abord résolu en `::1`, que Docker Desktop ne publie pas, et la connexion reste bloquée sans délai d'expiration.
- Sans Redis local, `/health/` répond 503 (`"redis": "error"`) : c'est le comportement attendu.
