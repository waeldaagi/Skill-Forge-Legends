from unittest import mock

from django.test import TestCase

from accounts.tests.factories import UserFactory
from core.ai import AIServiceError, run_ai_job
from core.ai.jobs import UNEXPECTED_ERROR_MESSAGE
from core.models import AIJob
from core.tests.fake_feature import FEATURE_NAME, make_feature, registered

TIMEOUT = AIServiceError("timeout", "Le service d'IA n'a pas répondu à temps.", retryable=True)
REJECTED_KEY = AIServiceError("http_error", "Le service d'IA a renvoyé une erreur (HTTP 401).")


class RunAIJobTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def run_job(self, feature, text="Quelqu'un a un exemple de prefetch_related ?"):
        with registered(feature), self.captureOnCommitCallbacks(execute=True):
            job = run_ai_job(FEATURE_NAME, self.user, target=self.user, payload={"text": text})
        job.refresh_from_db()
        return job

    def test_job_is_queued_only_once_the_transaction_commits(self):
        with registered(make_feature()), self.captureOnCommitCallbacks(execute=False) as callbacks:
            job = run_ai_job(FEATURE_NAME, self.user, target=self.user, payload={"text": "Bonjour"})

        self.assertEqual(job.status, AIJob.Status.PENDING)
        self.assertEqual(job.target, self.user)
        self.assertEqual(len(callbacks), 1)

    def test_job_succeeds_and_stores_the_validated_result(self):
        job = self.run_job(make_feature(), text="Promo exceptionnelle sur les formations")

        self.assertEqual(job.status, AIJob.Status.SUCCEEDED)
        self.assertEqual(job.result, {"label": "SPAM", "confidence": 0.9})
        self.assertIsNotNone(job.finished_at)

    def test_final_failure_applies_the_fallback_with_a_clear_message(self):
        fallback = mock.Mock()

        job = self.run_job(make_feature(run=mock.Mock(side_effect=REJECTED_KEY), fallback=fallback))

        self.assertEqual(job.status, AIJob.Status.FAILED)
        self.assertEqual(
            job.error_message,
            "Le service d'IA a renvoyé une erreur (HTTP 401). Un modérateur relira votre message.",
        )
        self.assertEqual(fallback.call_args.args[0].pk, job.pk)

    def test_rejected_key_is_not_retried(self):
        run = mock.Mock(side_effect=REJECTED_KEY)

        self.run_job(make_feature(run=run))

        self.assertEqual(run.call_count, 1)

    def test_network_errors_are_retried_twice_then_fail(self):
        run = mock.Mock(side_effect=TIMEOUT)
        fallback = mock.Mock()

        job = self.run_job(make_feature(run=run, fallback=fallback))

        self.assertEqual(run.call_count, 3)
        self.assertEqual(job.status, AIJob.Status.FAILED)
        fallback.assert_called_once()

    def test_a_passing_network_error_does_not_fail_the_job(self):
        run = mock.Mock(side_effect=[TIMEOUT, {"label": "OK", "confidence": 0.8}])
        fallback = mock.Mock()

        job = self.run_job(make_feature(run=run, fallback=fallback))

        self.assertEqual(job.status, AIJob.Status.SUCCEEDED)
        fallback.assert_not_called()

    def test_unexpected_error_still_ends_the_job_with_the_fallback(self):
        fallback = mock.Mock()

        with self.assertLogs("core.ai.jobs", "ERROR"):
            job = self.run_job(
                make_feature(run=mock.Mock(side_effect=KeyError("text")), fallback=fallback)
            )

        self.assertEqual(job.status, AIJob.Status.FAILED)
        self.assertTrue(job.error_message.startswith(UNEXPECTED_ERROR_MESSAGE))
        fallback.assert_called_once()

    def test_unregistered_feature_is_refused_before_creating_a_job(self):
        with self.assertRaises(LookupError):
            run_ai_job("fonctionnalite_inconnue", self.user)

        self.assertFalse(AIJob.objects.exists())
