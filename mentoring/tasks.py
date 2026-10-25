from celery import shared_task
from django.core.mail import send_mail

from .models import MentoringSession


@shared_task
def send_session_reminder(session_id):
    """Rappel 1 h avant, planifié à la confirmation (apply_async avec eta)."""
    session = (
        MentoringSession.objects.select_related("slot__mentor", "learner")
        .filter(pk=session_id, status=MentoringSession.Status.CONFIRMEE)
        .first()
    )
    # Annulée entre la planification et l'envoi : plus de rappel à faire.
    if session is None:
        return
    recipients = [user.email for user in (session.learner, session.mentor) if user.email]
    send_mail(
        "Rappel : votre session de mentorat commence dans 1 h",
        f"Session « {session.topic} » le {session.slot.period}.\n"
        "La salle de visio ouvre 15 minutes avant le début, depuis la page de la session.",
        None,
        recipients,
    )
