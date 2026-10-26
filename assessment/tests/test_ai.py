from unittest import mock

from django.test import TestCase

from assessment.ai.evaluation import run
from assessment.models import Submission
from assessment.services import keep_for_human_review
from assessment.tests.factories import CertificationFactory, LearnerFactory, ready_certification
from core.ai.jobs import execute_ai_job
from core.models import AIJob


class AssessmentAITests(TestCase):
    def setUp(self):
        self.learner = LearnerFactory()
        self.certification = ready_certification(CertificationFactory())
        self.submission = Submission.objects.create(
            learner=self.learner,
            certification=self.certification,
            text_response="Preuve propre",
            repository_url="",
            attempt_number=1,
            status=Submission.Status.EVALUATION_IA,
        )

    @mock.patch("assessment.ai.evaluation.complete_json")
    def test_run_applies_ai_output(self, complete_json):
        class Output:
            total_score = 78
            confidence = 0.73
            suspected_fraud = False
            fraud_reasons = []
            strengths = ["Bonne structure"]
            improvement_axes = ["Ajouter plus de tests"]

            class criterion:
                name = "Architecture"
                score = 75
                justification = "Bonne séparation"

            criteria = [criterion()]

        complete_json.return_value = Output()
        job = AIJob.objects.create(
            feature="assessment_evaluation", user=self.learner, target=self.submission
        )

        payload = run(job)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.EVALUEE_IA)
        self.assertEqual(payload["total_score"], 78)

    def test_fallback_keeps_submission_for_human_review(self):
        keep_for_human_review(self.submission)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.EN_REVUE)

    @mock.patch("assessment.ai.evaluation.complete_json", side_effect=Exception("boom"))
    def test_ai_job_failure_sets_failed_and_fallback(self, _complete_json):
        job = AIJob.objects.create(
            feature="assessment_evaluation", user=self.learner, target=self.submission
        )

        execute_ai_job.run(str(job.pk))

        job.refresh_from_db()
        self.submission.refresh_from_db()
        self.assertEqual(job.status, AIJob.Status.FAILED)
        self.assertEqual(self.submission.status, Submission.Status.EN_REVUE)
