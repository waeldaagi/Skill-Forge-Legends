from smtplib import SMTPException

from celery import shared_task
from django.core.mail import send_mail

# Celery ne cherche les tâches que dans les modules « tasks » : on y expose celle du socle IA.
from core.ai.jobs import execute_ai_job  # noqa: F401


@shared_task(autoretry_for=(SMTPException, OSError), retry_backoff=True, max_retries=3)
def send_email(subject, message, recipient_list, html_message=None):
    send_mail(subject, message, None, recipient_list, html_message=html_message)
