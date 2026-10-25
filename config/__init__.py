# Charge Celery avec Django pour que @shared_task utilise la configuration du projet.
from .celery import app as celery_app

__all__ = ("celery_app",)
