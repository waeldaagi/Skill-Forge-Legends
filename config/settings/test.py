from .base import *  # noqa: F403
from .base import env

# Valeur par défaut pour que la suite tourne sans .env ; aucune donnée réelle n'est signée.
SECRET_KEY = env("SECRET_KEY", default="tests-uniquement-pas-un-secret")

# MD5 : hachage volontairement rapide, réservé aux tests (des centaines d'utilisateurs créés).
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Jamais d'appel réel à une API d'IA dans les tests.
AI_PROVIDER = "mock"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Sortie des tests lisible : seuls les avertissements et les erreurs s'affichent.
LOGGING = {**LOGGING, "root": {"handlers": ["console"], "level": "WARNING"}}  # noqa: F405
