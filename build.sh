#!/usr/bin/env bash
# Commande de build de Render, relancée à chaque déploiement (voir DEPLOY.md).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py setup_roles
# Compte lu dans DJANGO_SUPERUSER_USERNAME, _EMAIL et _PASSWORD ; déjà créé ou absent : on continue.
python manage.py createsuperuser --noinput || true
# Comptes et données de démo, seulement si DEMO_PASSWORD est défini (seed_demo l'exige).
if [ -n "${DEMO_PASSWORD:-}" ]; then
  python manage.py seed_demo
fi
