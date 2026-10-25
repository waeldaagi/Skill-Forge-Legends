#!/usr/bin/env python
import os
import sys


def main():
    # « manage.py test » doit utiliser les mêmes réglages que pytest (Celery synchrone, IA mock).
    default_settings = (
        "config.settings.test" if sys.argv[1:2] == ["test"] else "config.settings.dev"
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", default_settings)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django est introuvable. Activez l'environnement virtuel (venv) "
            "puis lancez « pip install -r requirements-dev.txt »."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
