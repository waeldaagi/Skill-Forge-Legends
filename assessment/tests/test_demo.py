from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from assessment.models import Certification, Submission
from assessment.services import REVIEWABLE_STATUSES, verified_certificates


@override_settings(DEMO_PASSWORD="Demo-Certification-2026")
class AssessmentDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def test_demo_certification_is_open_with_a_complete_grid(self):
        certification = Certification.objects.get(course__slug="django-du-modele-au-deploiement")

        self.assertTrue(certification.is_active)
        self.assertEqual(certification.criteria_total, 100)

    def test_demo_learner_holds_a_certificate_visible_to_recruiters(self):
        learner = User.objects.get(username="yasmine.trabelsi")
        self.client.force_login(User.objects.get(username="oussema.mejri"))

        response = self.client.get(reverse("assessment:talent_search"))

        self.assertEqual(verified_certificates(learner).count(), 1)
        self.assertContains(response, str(learner))

    def test_one_submission_waits_for_the_mentor(self):
        self.client.force_login(User.objects.get(username="skander.jaziri"))

        response = self.client.get(reverse("assessment:review_queue"))

        pending = Submission.objects.filter(status__in=REVIEWABLE_STATUSES)
        self.assertEqual(pending.count(), 1)
        self.assertContains(response, str(pending.get().learner))

    def test_seed_can_run_again_without_duplicates(self):
        call_command("seed_demo", stdout=StringIO())

        self.assertEqual(Submission.objects.count(), 2)
