from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import UserFactory
from core.models import AIJob
from core.tests.fake_feature import FEATURE_NAME, make_feature, registered


class AIStatusTestCase(TestCase):
    def setUp(self):
        patcher = registered(make_feature())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.owner = UserFactory()
        self.job = AIJob.objects.create(feature=FEATURE_NAME, user=self.owner)
        self.url = reverse("core:ai_job_status", args=[self.job.pk])


class AIJobStatusViewTests(AIStatusTestCase):
    def test_owner_sees_the_progress_message_while_the_job_runs(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/partials/ai_status.html")
        self.assertContains(response, "Classement de votre message en cours…")

    def test_finished_job_answers_286_to_stop_the_polling(self):
        self.job.mark_succeeded({"label": "OK", "confidence": 0.9})
        self.client.force_login(self.owner)

        response = self.client.get(self.url)

        self.assertContains(response, "Traitement terminé.", status_code=286)

    def test_failed_job_shows_its_error_message(self):
        self.job.mark_failed("Le service d'IA est injoignable. Un modérateur relira votre message.")
        self.client.force_login(self.owner)

        response = self.client.get(self.url)

        self.assertContains(response, "Un modérateur relira votre message.", status_code=286)

    def test_another_user_cannot_read_the_job(self):
        self.client.force_login(UserFactory())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_anonymous_visitor_is_sent_to_the_login_page(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")


class AIJobStatusTagTests(AIStatusTestCase):
    def render_region(self):
        template = Template("{% load ai_status %}{% ai_job_status job %}")
        return template.render(Context({"job": self.job}))

    def test_running_job_region_polls_every_two_seconds(self):
        html = self.render_region()

        self.assertIn('role="status"', html)
        self.assertIn(f'hx-get="{self.url}"', html)
        self.assertIn('hx-trigger="every 2s"', html)

    def test_finished_job_region_no_longer_polls(self):
        self.job.mark_succeeded({"label": "OK", "confidence": 0.9})

        html = self.render_region()

        self.assertNotIn("hx-get", html)
        self.assertIn("Traitement terminé.", html)
