import logging
from functools import partial

from celery import shared_task
from django.db import transaction

from core.models import AIJob

from .exceptions import AIServiceError
from .features import get_feature

logger = logging.getLogger(__name__)

# Un appel initial puis deux relances au maximum, uniquement sur une erreur passagère.
MAX_NETWORK_RETRIES = 2
UNEXPECTED_ERROR_MESSAGE = "Le traitement automatique s'est arrêté sur une erreur inattendue."


def run_ai_job(feature, user, target=None, payload=None):
    """Crée un AIJob en attente et confie son exécution à Celery.

    La tâche part après la validation de la transaction : le worker trouve toujours le job en base.
    """
    get_feature(feature)  # Une fonctionnalité non enregistrée échoue ici, pas dans le worker.
    job = AIJob.objects.create(feature=feature, user=user, target=target, payload=payload or {})
    transaction.on_commit(partial(execute_ai_job.delay, str(job.pk)))
    return job


@shared_task(bind=True, max_retries=MAX_NETWORK_RETRIES)
def execute_ai_job(self, job_id):
    job = AIJob.objects.get(pk=job_id)
    feature = get_feature(job.feature)
    job.mark_running()
    try:
        result = feature.run(job)
    except AIServiceError as exc:
        if exc.retryable and self.request.retries < self.max_retries:
            # Backoff progressif : Gemini peut renvoyer 503 pendant quelques secondes.
            countdown = 5 * (self.request.retries + 1)
            raise self.retry(exc=exc, countdown=countdown) from exc
        _fail(job, feature, exc.user_message)
    except Exception:
        # Bord du système : une erreur de programmation ne doit pas laisser le job « en cours ».
        logger.exception("Tâche IA %s (%s) : erreur inattendue", job.pk, job.feature)
        _fail(job, feature, UNEXPECTED_ERROR_MESSAGE)
    else:
        job.mark_succeeded(result)


def _fail(job, feature, reason):
    job.mark_failed(f"{reason} {feature.failure_message}")
    feature.fallback(job)
