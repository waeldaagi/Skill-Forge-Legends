from django.core import mail
from django.test import TestCase, override_settings

from core.services import queue_email
from core.tasks import send_email


class SendEmailTaskTests(TestCase):
    @override_settings(DEFAULT_FROM_EMAIL="SkillForge <no-reply@skillforge.tn>")
    def test_sends_from_the_platform_address(self):
        send_email.delay(
            "Session confirmée", "Votre session est confirmée.", ["ines@skillforge.test"]
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "SkillForge <no-reply@skillforge.tn>")
        self.assertEqual(mail.outbox[0].to, ["ines@skillforge.test"])


class QueueEmailTests(TestCase):
    def test_email_leaves_once_the_transaction_commits(self):
        with self.captureOnCommitCallbacks(execute=True):
            queue_email(
                "Réservation reçue", "Votre demande est transmise.", ["amine@skillforge.test"]
            )

        self.assertEqual(mail.outbox[0].subject, "Réservation reçue")

    def test_no_email_while_the_transaction_is_open(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            queue_email(
                "Réservation reçue", "Votre demande est transmise.", ["amine@skillforge.test"]
            )

        self.assertEqual(len(callbacks), 1)
        self.assertEqual(mail.outbox, [])
