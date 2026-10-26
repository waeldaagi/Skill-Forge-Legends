# Sécurité et contrôle d'accès

Ce document relie chaque exigence de sécurité de la grille de validation à sa preuve dans le code et dans les tests. État au 26/10/2026, branche `release/v1`.

## 1. Bases OWASP pour Django

| Exigence | Mise en œuvre | Preuve |
|---|---|---|
| Protection CSRF active | `CsrfViewMiddleware` dans `MIDDLEWARE` ; `{% csrf_token %}` dans chaque formulaire POST ; jeton envoyé par HTMX (`hx-headers` dans `base.html`) | Aucun `csrf_exempt` dans le code (recherche ci-dessous) ; page 403 dédiée aux échecs CSRF (`core/tests/test_errors.py`) |
| Pas d'injection SQL | Uniquement l'ORM : aucun `.raw()`, `cursor()`, `.extra()` ni `RawSQL` | Recherche ci-dessous |
| Mots de passe hachés | Hacheur par défaut de Django (PBKDF2), quatre validateurs (`AUTH_PASSWORD_VALIDATORS`) | MD5 seulement dans `config/settings/test.py`, pour accélérer les tests |
| `DEBUG = False` en production | `config/settings/prod.py` force `DEBUG = False` ; `ALLOWED_HOSTS` obligatoire hors Render | `core/tests/test_prod_settings.py` ; `check --deploy` sans remarque, lancé dans l'image Docker par la CI |
| Secrets hors du code | `SECRET_KEY`, `AI_API_KEY`, `DEMO_PASSWORD`, identifiants de base : variables d'environnement (`.env` ignoré par Git, Render ou serveur) | Recherche dans l'historique ci-dessous |
| HTTPS | `SECURE_SSL_REDIRECT`, HSTS d'un an, cookies de session et CSRF `Secure`, `SECURE_PROXY_SSL_HEADER` pour le proxy | Simulation Render : une requête HTTP reçoit 301 vers HTTPS, un hôte inconnu reçoit 400 (`DEPLOY.md`, section 8) |
| Contenu des utilisateurs échappé | Échappement automatique des gabarits ; `linebreaks` pour les messages du forum | Un seul `\|safe`, sur les textes d'aide des formulaires, écrits par les développeurs |
| Fichiers envoyés | Extensions en liste blanche (`FileExtensionValidator`) et 5 Mo au maximum (`core.validators.validate_upload_size`) | `core/tests/test_validators.py`, `courses/tests/test_views.py`, `accounts/tests/test_views.py` |
| Prompt de l'IA | Texte de l'utilisateur délimité (`delimit_user_content`), consigne anti-injection, sortie validée par un schéma pydantic | `community/tests/test_moderation_ai.py` (`test_user_text_cannot_escape_its_delimiters`) |

## 2. Contrôle d'accès par rôle

Chaque vue privée passe par `RoleRequiredMixin` (rôle autorisé, sinon 403) ou `OwnerRequiredMixin` (l'objet d'un autre utilisateur donne 404). Les groupes Django suivent le rôle (`setup_roles`), et l'admin Django est réservé au rôle administrateur.

Contourner un accès par URL directe est testé à trois niveaux :

| Niveau | Test | Ce qu'il prouve |
|---|---|---|
| Toutes les URL du projet | `core/tests/test_url_protection.py` | Les 81 URL nommées sont découvertes automatiquement ; hors des 13 pages publiques listées, un anonyme est renvoyé vers la connexion. Une nouvelle vue sans contrôle d'accès fait échouer la CI. |
| Chaque module | `test_permissions.py` de `courses` (26 URL), `mentoring` (16 URL) et `community` (19 URL) | Pour chaque URL, le statut attendu pour les six rôles et l'anonyme : 200, 302, 403 ou 404 |
| Tout le site sur les données de démo | `core/tests/test_site_crawl.py` | Pour chaque rôle, chaque lien affiché est suivi : aucun lien ne mène à une page interdite (403), introuvable (404) ou en erreur (500) |

Exemples de règles vérifiées : le cours d'un autre formateur donne 404 ; un quiz premium sans abonnement donne 404, même par URL directe ; seul un apprenant répond à un quiz ou rejoint un établissement ; un mentor ou un formateur non vérifié ne publie rien.

## 3. Robustesse et gestion des erreurs

- Pages 403, 404, 500 et échec CSRF personnalisées (`templates/`), branchées par `handler403`, `handler404` et `handler500`.
- Exceptions métier précises (`SlotUnavailable`, `CancellationTooLate`…) traduites en messages pour l'utilisateur.
- IA : erreurs HTTP et délais traduits en `AIServiceError`, deux relances sur erreur passagère, puis repli métier (file de modération humaine, quiz à compléter à la main).
- Redis arrêté : la requête aboutit, la tâche part en repli au lieu d'une erreur 500 (`core.dispatch.enqueue`).
- Formulaires : validation côté serveur (`clean()`, contraintes en base doublées dans les formulaires) et côté navigateur (attributs HTML5, aucun `novalidate`).

## 4. Recherches du 26/10/2026

Code (hors `venv/`) :

```
grep -rnE "\.raw\(|cursor\(\)|\.extra\(|RawSQL|csrf_exempt|mark_safe|\|safe|eval\(|exec\(|pickle|shell=True" --include=*.py --include=*.html .
```

Résultat : une seule ligne, `core/templates/core/forms/field.html` (`help_text|safe`, voir le tableau de la section 1).

Historique Git complet (`git log -p --all`), zéro occurrence pour chacun de ces motifs : clé Google (`AIza…`), clé OpenAI (`sk-…`), clé privée (`BEGIN … PRIVATE KEY`), jeton GitHub (`ghp_…`), clé AWS (`AKIA…`), `SECRET_KEY` écrite en dur, `AI_API_KEY` renseignée. Le fichier `.env` n'apparaît dans aucun commit.
