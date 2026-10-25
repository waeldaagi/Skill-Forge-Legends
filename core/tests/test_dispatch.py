from unittest import mock

from django.core import mail
from django.test import TestCase
from kombu.exceptions import OperationalError

from core.dispatch import enqueue
from core.services import queue_email
from core.tasks import send_email

REDIS_DOWN = OperationalError("Error 10061 connecting to 127.0.0.1:6379.")


class EnqueueTests(TestCase):
    def test_task_is_handed_to_celery(self):
        self.assertTrue(enqueue(send_email, "Sujet", "Message", ["ines@skillforge.test"]))

        self.assertEqual(len(mail.outbox), 1)

    def test_unreachable_redis_is_logged_instead_of_raised(self):
        with (
            mock.patch.object(send_email, "apply_async", side_effect=REDIS_DOWN),
            self.assertLogs("core.dispatch", "ERROR"),
        ):
            self.assertFalse(enqueue(send_email, "Sujet", "Message", ["ines@skillforge.test"]))

    def test_email_after_a_booking_does_not_break_the_request_when_redis_is_down(self):
        with (
            mock.patch.object(send_email, "apply_async", side_effect=REDIS_DOWN),
            self.assertLogs("core.dispatch", "ERROR"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            queue_email(
                "Réservation reçue", "Votre demande est transmise.", ["amine@skillforge.test"]
            )

        self.assertEqual(mail.outbox, [])
