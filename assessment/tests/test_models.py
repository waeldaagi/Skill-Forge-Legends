from django.core.exceptions import ValidationError
from django.test import TestCase

from assessment.models import Criterion, Submission
from assessment.tests.factories import CertificationFactory, LearnerFactory, ready_certification


class AssessmentModelTests(TestCase):
    def test_certification_active_requires_criteria_total_100(self):
        certification = CertificationFactory(is_active=True)
        Criterion.objects.create(
            certification=certification,
            name="Architecture",
            description="Structure",
            weight=80,
        )

        with self.assertRaises(ValidationError):
            certification.full_clean()

    def test_submission_requires_at_least_one_piece_of_evidence(self):
        learner = LearnerFactory()
        certification = ready_certification(CertificationFactory())
        submission = Submission(
            learner=learner,
            certification=certification,
            text_response="",
            repository_url="",
            attempt_number=1,
        )

        with self.assertRaises(ValidationError):
            submission.full_clean()
