# Déployer SkillForge sur Render

SkillForge se déploie sur Render en suivant l'atelier « Déploiement d'une application Django sur Render » (UP-Web, 2025-2026). Deux voies mènent au même résultat : le Blueprint `render.yaml` (section 2) ou les étapes manuelles de l'atelier (section 3).

## 1. Correspondance avec l'atelier

| Étape de l'atelier | Dans SkillForge |
|---|---|
| PostgreSQL avec `psycopg2-binary` et `dj-database-url` | `psycopg[binary]` (psycopg 3) et `env.db("DATABASE_URL")` de django-environ, dans `config/settings/base.py`. Sans `DATABASE_URL`, SQLite en local. |
| WhiteNoise juste après `SecurityMiddleware` | Déjà en place dans `MIDDLEWARE` (`base.py`) |
| `STATIC_ROOT` et `CompressedManifestStaticFilesStorage` | `STATIC_ROOT = staticfiles` (`base.py`) ; stockage WhiteNoise dans `config/settings/prod.py` |
| `DEBUG = False` en production | `config/settings/prod.py`, choisi par `DJANGO_SETTINGS_MODULE=config.settings.prod` |
| `ALLOWED_HOSTS`, `RENDER_EXTERNAL_HOSTNAME`, `CSRF_TRUSTED_ORIGINS` | `prod.py` ajoute le nom d'hôte fourni par Render aux deux listes |
| Script `build.sh` | `build.sh` à la racine, exécutable : dépendances, `collectstatic`, `migrate`, `createsuperuser`, plus `setup_roles` et `seed_demo` |
| Gunicorn et Uvicorn | Gunicorn seul : `python -m gunicorn config.wsgi:application`. Le projet n'a aucune vue asynchrone ; le mode WSGI évite une dépendance. |
| `WEB_CONCURRENCY = 4` | 2 : l'offre gratuite donne 512 Mo de mémoire, et chaque processus Django en occupe une partie |

## 2. Déployer avec le Blueprint

Prérequis : un compte Render relié à GitHub, et la branche `main` à jour (fusion de `develop` dans `main`).

1. Sur [dashboard.render.com](https://dashboard.render.com), cliquer sur **New**, puis **Blueprint**.
2. Choisir le dépôt `waeldaagi/Skill-Forge-Legends`, branche `main`. Render lit `render.yaml` et annonce deux ressources : la base `skillforge-db` (PostgreSQL, offre gratuite, Francfort) et le service web `skillforge`.
3. Renseigner les variables que le Blueprint laisse vides (tableau de la section 4) : `DEMO_PASSWORD`, `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`. `AI_API_KEY` peut rester vide tant que `AI_PROVIDER` vaut `mock`.
4. Cliquer sur **Apply**. Render crée la base, lance `build.sh`, puis démarre gunicorn. L'adresse publique s'affiche en haut de la page du service, par exemple `https://skillforge.onrender.com`.

## 3. Déployer à la main (étapes de l'atelier)

1. **New**, puis **Postgres** : nom `skillforge-db`, région Frankfurt, offre Free. Sur la page de la base, copier l'**Internal Database URL**.
2. **New**, puis **Web Service** : choisir le dépôt, langage Python 3, branche `main`, région Frankfurt, instance Free.
3. Build Command : `./build.sh`. Start Command : `python -m gunicorn config.wsgi:application`.
4. Ajouter les variables d'environnement de la section 4. `DATABASE_URL` reçoit l'Internal Database URL copiée à l'étape 1 ; `SECRET_KEY` se génère avec le bouton **Generate**.
5. Dans **Advanced**, Health Check Path : `/health/`.
6. Cliquer sur **Create Web Service**.

## 4. Variables d'environnement

| Variable | Valeur | Rôle |
|---|---|---|
| `PYTHON_VERSION` | `3.12.10` | Même version que le projet |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | Sans elle, `manage.py` charge les réglages de développement |
| `DATABASE_URL` | Internal Database URL de la base | Connexion à PostgreSQL |
| `SECRET_KEY` | Générée par Render | Signature des sessions et des jetons CSRF |
| `WEB_CONCURRENCY` | `2` | Nombre de processus gunicorn |
| `CELERY_TASK_ALWAYS_EAGER` | `True` | Pas de worker Celery sur l'offre gratuite : les tâches tournent dans le processus web |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Sans serveur SMTP, les e-mails s'écrivent dans les journaux du service |
| `SERVE_MEDIA` | `True` | Django sert lui-même les fichiers envoyés (avatars, images de cours, ressources) |
| `AI_PROVIDER` | `mock`, ou `gemini` | `mock` répond sans réseau ; `gemini` appelle l'API réelle |
| `AI_API_KEY` | Clé Gemini, ou vide | Uniquement dans Render, jamais dans le dépôt |
| `DEMO_PASSWORD` | Mot de passe choisi | Si défini, `build.sh` lance `seed_demo` : un compte par rôle et les données de démo |
| `DJANGO_SUPERUSER_USERNAME`, `_EMAIL`, `_PASSWORD` | Compte administrateur | Lus par `createsuperuser --noinput` ; ignorés si le compte existe déjà |

`RENDER`, `RENDER_EXTERNAL_HOSTNAME` et `PORT` sont fournis par Render : il ne faut pas les définir.

## 5. Vérifier le déploiement

1. `https://<service>.onrender.com/health/` répond `{"status": "ok", "database": "ok", "redis": "not_used"}`.
2. La page d'accueil s'affiche, avec les styles (fichiers statiques servis par WhiteNoise).
3. Connexion avec un compte de démo (`yasmine.trabelsi`, mot de passe `DEMO_PASSWORD`), puis publication d'un sujet sur le forum : la vérification automatique le publie.
4. `/admin/` s'ouvre avec le compte `DJANGO_SUPERUSER_USERNAME`.
5. « Mot de passe oublié » : l'e-mail apparaît dans l'onglet **Logs** du service.

## 6. Activer l'IA réelle (Gemini)

Dans l'onglet **Environment** du service : `AI_PROVIDER=gemini` et `AI_API_KEY=<clé>`, puis **Save Changes**. Render redéploie le service. La clé reste dans Render ; elle n'apparaît ni dans le dépôt ni dans les journaux.

## 7. Limites de l'offre gratuite

- **Mise en veille.** Le service s'arrête après une période sans visite ; la requête suivante attend son redémarrage, environ une minute. Ouvrir le site quelques minutes avant une démonstration.
- **Tâches dans la requête.** Sans worker, la modération (environ 1 s avec Gemini) et la génération de quiz (jusqu'à 60 s) s'exécutent pendant la requête. Le rappel de session part à la réservation au lieu d'une heure avant.
- **Disque éphémère.** Les fichiers envoyés disparaissent à chaque redéploiement. Les données de démo, elles, sont recréées par `seed_demo` à chaque build.
- **Base gratuite à durée limitée.** Render affiche sa date d'expiration sur la page de la base.

Avec une offre payante : un Background Worker pour Celery, une base Key Value pour Redis, et un disque persistant ou un stockage objet pour les médias.

## 8. Vérification locale du 26/10/2026

Le déploiement a été simulé dans un conteneur `python:3.12-slim` relié à un conteneur `postgres:16`, avec les variables du tableau ci-dessus et sans le fichier `.env` local.

| Contrôle | Résultat |
|---|---|
| `build.sh` | Dépendances installées, toutes les migrations appliquées, 6 groupes de rôles, superutilisateur et données de démo créés |
| Démarrage | Gunicorn écoute sur `$PORT` avec 2 processus |
| `/health/` | 200, Redis « not_used » |
| Accueil, catalogue, connexion, offres, feuille de style | 200 |
| Page inexistante | 404 personnalisée |
| Requête en HTTP | 301 vers HTTPS |
| Hôte inconnu | 400 |
| Connexion, sujet de forum, réinitialisation du mot de passe, avatar | Sujet publié par la modération (`mock`), e-mail écrit dans le journal, avatar servi en 200 |

## 9. Variante : pile Docker sur un serveur

Pour un serveur avec Docker (machine virtuelle Azure for Students, par exemple), `docker-compose.prod.yml` démarre cinq services : `web` (gunicorn), `worker` et `beat` (Celery), `db` (PostgreSQL 16) et `redis` (Redis 7). Contrairement à l'offre gratuite de Render, les tâches IA passent par le worker et ne bloquent pas la requête.

```
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py seed_demo
```

Le fichier `.env` du serveur fournit `SECRET_KEY`, `ALLOWED_HOSTS`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, et au besoin `DEMO_PASSWORD`, `AI_PROVIDER`, `AI_API_KEY`, `EMAIL_*`. Un autre fichier se désigne avec la variable `ENV_FILE`.

L'image (`Dockerfile`) part de `python:3.12-slim`, collecte les fichiers statiques au build et tourne sous un utilisateur non root. Le service `web` applique les migrations à son démarrage (`docker/entrypoint.sh`), et Docker le déclare sain quand `/health/` répond 200. Le HTTPS est attendu d'un proxy placé devant (Caddy ou nginx), qui transmet `X-Forwarded-Proto`.

Vérifié le 26/10/2026 : les cinq services démarrent, `web` passe à l'état sain, `/health/` répond avec la base et Redis à « ok », et un sujet de forum créé « En attente » est publié par le worker Celery en 73 ms (fournisseur `mock`). La CI construit l'image à chaque push et lance `check --deploy` dedans.
