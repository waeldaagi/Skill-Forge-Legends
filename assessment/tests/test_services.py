from unittest import mock

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from assessment.models import HumanReview, Submission
from assessment.services import (
    apply_ai_evaluation,
    finalize_human_review,
    submit_submission,
)
from assessment.tests.factories import (
    CertificationFactory,
    LearnerFactory,
    MentorFactory,
    ready_certification,
)


class AssessmentServiceTests(TestCase):
    @mock.patch("assessment.services.learner_can_submit", return_value=True)
    def test_submit_submission_creates_attempt_one(self, _can_submit):
        learner = LearnerFactory()
        certification = ready_certification(CertificationFactory())

        submission = submit_submission(
            learner=learner,
            certification=certification,
            text_response="Preuve solide",
            repository_url="",
            attachment=None,
        )

        self.assertEqual(submission.attempt_number, 1)
        self.assertEqual(submission.status, Submission.Status.EVALUATION_IA)

    @mock.patch("assessment.services.learner_can_submit", return_value=False)
    def test_submit_submission_refuses_ineligible_learner(self, _can_submit):
        learner = LearnerFactory()
        certification = ready_certification(CertificationFactory())

        with self.assertRaises(PermissionDenied):
            submit_submission(
                learner=learner,
                certification=certification,
                text_response="Preuve",
                repository_url="",
                attachment=None,
            )

    @mock.patch("assessment.services.learner_can_submit", return_value=True)
    def test_submit_submission_blocks_after_max_attempts(self, _can_submit):
        learner = LearnerFactory()
        certification = ready_certification(CertificationFactory(max_attempts=1))
        submit_submission(
            learner=learner,
            certification=certification,
            text_response="Tentative 1",
            repository_url="",
            attachment=None,
        )

        with self.assertRaises(ValidationError):
            submit_submission(
                learner=learner,
                certification=certification,
                text_response="Tentative 2",
                repository_url="",
                attachment=None,
            )

    @mock.patch("assessment.services._similarity_score", return_value=0.9)
    def test_apply_ai_evaluation_flags_fraud_on_similarity(self, _score):
        learner = LearnerFactory()
        certification = ready_certification(CertificationFactory())
        submission = Submission.objects.create(
            learner=learner,
            certification=certification,
            text_response="texte",
            repository_url="",
            attempt_number=1,
            status=Submission.Status.EVALUATION_IA,
        )

        evaluation = apply_ai_evaluation(
            submission=submission,
            result={
                "total_score": 75,
                "criteria_scores": {"Architecture": {"score": 70, "justification": "ok"}},
                "strengths": ["clair"],
                "improvement_axes": ["plus de tests"],
                "confidence": 0.7,
                "suspected_fraud": False,
                "fraud_reasons": [],
            },
            provider="mock",
            duration_ms=120,
        )

        self.assertTrue(evaluation.suspected_fraud)
        self.assertIn("Similarité TF-IDF", evaluation.fraud_reasons)

    def test_human_review_success_issues_certificate(self):
        learner = LearnerFactory()
        reviewer = MentorFactory()
        certification = ready_certification(CertificationFactory())
        submission = Submission.objects.create(
            learner=learner,
            certification=certification,
            text_response="preuve",
            repository_url="",
            attempt_number=1,
            status=Submission.Status.EVALUEE_IA,
        )

        review, certificate = finalize_human_review(
            submission=submission,
            reviewer=reviewer,
            final_score=85,
            decision=HumanReview.Decision.REUSSIE,
            comment="Bon niveau",
            overrides_ai=False,
        )

        self.assertEqual(review.decision, HumanReview.Decision.REUSSIE)
        self.assertIsNotNone(certificate)
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.REUSSIE)
