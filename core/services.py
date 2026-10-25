from functools import partial

from django.db import transaction

from .tasks import send_email


def queue_email(subject, message, recipient_list, html_message=None):
    """Confie l'e-mail à Celery une fois la transaction validée.

    Si la transaction échoue (réservation refusée, par exemple), aucun e-mail ne part.
    """
    transaction.on_commit(partial(send_email.delay, subject, message, recipient_list, html_message))
