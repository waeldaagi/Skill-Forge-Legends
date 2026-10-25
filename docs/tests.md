# Tests et couverture

## Lancer la suite

```
python manage.py test                 # ou : pytest
pytest --cov --cov-report=term --cov-report=html
```

Les deux commandes utilisent `config.settings.test` : Celery exécute les tâches dans le processus de test, le fournisseur d'IA est `mock` et aucun appel réseau n'est fait. Le rapport HTML est écrit dans `htmlcov/index.html`.

La CI GitHub Actions lance la même suite sur PostgreSQL 16 et Redis 7, refuse une couverture inférieure à 75 % et publie `htmlcov` comme artefact de chaque exécution.

Sont exclus de la mesure : migrations, settings, `manage.py`, `asgi.py`, `wsgi.py` et les dossiers `tests/` eux-mêmes.

## Résultats au 25/10/2026 (fin de la Phase 0)

Commande : `pytest --cov`, sur SQLite. Couverture des instructions et des branches.

| App | Tests | Instructions | Non couvertes | Couverture |
|---|---|---|---|---|
| `core` | 70 | 404 | 2 | 99,1 % |
| `accounts` | 19 | 87 | 0 | 100 % |
| `config` | — | 18 | 1 | 90,0 % |
| `courses` | 0 | 12 | 6 | 50,0 % |
| `assessment` | 0 | 8 | 2 | 75,0 % |
| `payments` | 0 | 8 | 2 | 75,0 % |
| `mentoring`, `community`, `analytics` | 0 | 6 chacune | 0 | 100 % |
| **Total** | **89** | **555** | **13** | **97,3 %** |

Les apps métier ne contiennent encore que leur configuration et les stubs des contrats entre modules (`courses.services`, `payments.services`, `assessment.services`). Ces stubs ne sont pas testés : ils seront remplacés par leur responsable, avec ses propres tests. Leur couverture n'a donc pas de sens à ce stade ; elle en prendra dès les Phases 1 à 4.

## Ce que les tests prouvent

| Fichier | Règles vérifiées |
|---|---|
| `accounts/tests/test_models.py` | Le groupe suit le rôle à la création et au changement de rôle ; seul le rôle ADMIN ouvre l'admin Django ; `createsuperuser` crée un administrateur. |
| `accounts/tests/test_commands.py` | `setup_roles` crée un groupe par rôle, donne les permissions déclarées, peut être relancée, refuse une permission ou un rôle inconnus. |
| `accounts/tests/test_views.py` | Connexion, mot de passe faux, déconnexion. |
| `core/tests/test_permissions.py` | Chaque mixin, pour chaque rôle autorisé et refusé ; l'objet d'un autre utilisateur donne 404. |
| `core/tests/test_ai_client.py` | Sortie validée par pydantic ; journalisation sans donnée personnelle ; timeout, erreurs HTTP et service injoignable ; une seule relance sur réponse invalide ; consigne anti-injection. |
| `core/tests/test_ai_gemini.py` | Clé dans l'en-tête, JSON imposé, modèle configurable, erreur 503, réponse bloquée, clé absente (réponses HTTP simulées). |
| `core/tests/test_ai_jobs.py` | Tâche lancée après la validation de la transaction ; succès ; échec avec repli ; deux relances sur erreur passagère ; aucune relance sur clé refusée ; erreur inattendue. |
| `core/tests/test_ai_status.py` | Statut réservé au propriétaire ; code 286 en fin de traitement ; zone `role="status"` qui interroge le serveur toutes les 2 s tant que le job tourne. |
| `core/tests/test_admin.py` | Journal des appels IA en lecture seule dans l'admin ; lisible par un administrateur grâce aux permissions de son groupe. |
| `core/tests/test_errors.py` | Handlers 403, 404 et 500 branchés ; page d'échec CSRF avec consigne. |
| `core/tests/test_forms.py` | Libellé, mention « (obligatoire) », classes Bootstrap, erreur reliée au champ par `aria-describedby`. |
| `core/tests/test_views.py` | Accueil, repères accessibles, un seul `<h1>`, navigation selon le rôle, `aria-current`. |
| `core/tests/test_health.py` | `/health/` : 200 si la base et Redis répondent, 503 sinon, jamais en cache. |
| `core/tests/test_emails.py` | Adresse d'expédition ; e-mail envoyé seulement après la validation de la transaction. |

## Lignes non couvertes

- `core/models.py`, `AIJob.__str__` : affichage dans l'admin, sans règle métier.
- `core/forms.py`, branche « widget caché » : aucun formulaire du projet n'a encore de champ caché.
- `config/urls.py`, route des médias en `DEBUG` : jamais active en test (Django force `DEBUG=False`).
- Stubs de `courses`, `assessment` et `payments` : voir plus haut.
