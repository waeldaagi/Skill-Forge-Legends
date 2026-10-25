from celery import shared_task

from .services import expire_subscriptions


@shared_task
def expire_subscriptions_task():
    """Met à jour quotidiennement les abonnements arrivés à échéance."""
    return expire_subscriptions()
