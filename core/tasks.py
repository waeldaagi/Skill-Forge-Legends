from smtplib import SMTPException

from celery import shared_task
from django.core.mail import send_mail


@shared_task(autoretry_for=(SMTPException, OSError), retry_backoff=True, max_retries=3)
def send_email(subject, message, recipient_list, html_message=None):
    send_mail(subject, message, None, recipient_list, html_message=html_message)
