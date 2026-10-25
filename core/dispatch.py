"""Envoi des tâches à Celery sans faire échouer la requête de l'utilisateur."""

import logging

from kombu.exceptions import OperationalError

logger = logging.getLogger(__name__)


def enqueue(task, *args, **options):
    """Confie la tâche à Celery ; renvoie False si la file (Redis) est injoignable.

    Une panne de Redis ne doit pas transformer une action déjà enregistrée en erreur 500 :
    l'appelant décide du repli (file humaine, e-mail perdu journalisé).
    """
    try:
        task.apply_async(args=args, **options)
    except OperationalError:
        logger.exception("File Celery injoignable : tâche %s non envoyée", task.name)
        return False
    return True
