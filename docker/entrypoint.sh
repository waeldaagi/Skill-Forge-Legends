#!/bin/sh
# Le service web applique les migrations avant de démarrer ; le worker et beat ne le font pas,
# pour éviter deux migrations simultanées.
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --no-input
  python manage.py setup_roles
fi

exec "$@"
