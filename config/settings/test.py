from .base import *  # noqa: F403
from .base import env

# Valeur par défaut pour que la suite tourne sans .env ; aucune donnée réelle n'est signée.
SECRET_KEY = env("SECRET_KEY", default="tests-uniquement-pas-un-secret")

# MD5 : hachage volontairement rapide, réservé aux tests (des centaines d'utilisateurs créés).
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Tâches exécutées dans le processus de test. Sans CELERY_TASK_EAGER_PROPAGATES : Celery rejoue
# alors les relances (self.retry) comme un worker ; une tâche en échec reste journalisée.
CELERY_TASK_ALWAYS_EAGER = True

# Jamais d'appel réel à une API d'IA dans les tests.
AI_PROVIDER = "mock"

# Pas de collectstatic en test : WhiteNoise cherche les fichiers à la demande.
WHITENOISE_AUTOREFRESH = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Sortie des tests lisible : seuls les avertissements et les erreurs s'affichent. Les 403 et 404
# voulus par les tests de permissions ne sont pas journalisés ; une erreur 500 le reste.
LOGGING = {  # noqa: F405
    **LOGGING,  # noqa: F405
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"django.request": {"level": "ERROR"}},
}
