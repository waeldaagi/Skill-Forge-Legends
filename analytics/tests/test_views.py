from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from payments.models import Plan
from payments.services import simulate_payment


class AnalyticsViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory(role=User.Role.APPRENANT)
        self.plan = Plan.objects.create(
            name="Premium", slug="premium", price=Decimal("29.900"), duration_days=30
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("analytics:dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('analytics:dashboard')}",
        )

    def test_ai_analytics_are_reserved_to_administrators(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/analytics/").status_code, 403)

        self.client.force_login(UserFactory(role=User.Role.ADMIN))
        self.assertEqual(self.client.get("/analytics/").status_code, 200)

    def test_pilotage_has_its_own_interface(self):
        self.client.force_login(self.user)
        response = self.client.get("/pilotage/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de pilotage")

    def test_apprentice_sees_own_payment_metrics(self):
        simulate_payment(self.user, self.plan)
        self.client.force_login(self.user)

        response = self.client.get(reverse("pilotage"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["metrics"]["successful_payments"], 1)
        self.assertContains(response, "29,900")

    def test_pilotage_provides_chart_data(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("pilotage"))

        self.assertEqual(response.context["chart_data"]["Paiements réussis"], 0)
        self.assertContains(response, "analytics-chart-data")

    def test_csv_export_is_available_to_authenticated_users(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("analytics:export"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("Indicateur", response.content.decode())

    def test_admin_metrics_include_platform_totals(self):
        admin = UserFactory(role=User.Role.ADMIN)

        self.client.force_login(admin)
        response = self.client.get(reverse("analytics:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("users", response.context["metrics"])
        self.assertIn("platform_revenue", response.context["metrics"])

    def test_analytics_shows_dropout_training_summary(self):
        self.client.force_login(UserFactory(role=User.Role.ADMIN))

        response = self.client.get(reverse("analytics:dashboard"))

        self.assertTrue(response.context["dropout"]["available"])
        self.assertGreater(response.context["dropout"]["dropout_rate"], 0)
        self.assertContains(response, "Taux d'abandon")


class AnalyticsMetricsTests(TestCase):
    def test_pilotage_reads_real_course_progress_and_sessions(self):
        from courses.services import mark_chapter_completed
        from courses.tests.factories import ChapterFactory
        from mentoring.tests.factories import MentoringSessionFactory

        learner = UserFactory(role=User.Role.APPRENANT)
        first = ChapterFactory(order=1)
        ChapterFactory(course=first.course, order=2)
        mark_chapter_completed(learner, first)
        MentoringSessionFactory(learner=learner)
        self.client.force_login(learner)

        metrics = self.client.get(reverse("pilotage")).context["metrics"]

        self.assertEqual((metrics["course_progress"], metrics["mentoring_sessions"]), (50, 1))

    def test_csv_export_uses_french_labels_and_details_ai_failures(self):
        from core.models import AICallLog

        AICallLog.objects.create(
            feature="moderation", provider="gemini", duration_ms=900, success=False
        )
        self.client.force_login(UserFactory(role=User.Role.ADMIN))

        content = self.client.get(reverse("analytics:export")).content.decode()

        self.assertIn("Abonnements actifs", content)
        self.assertIn("Taux d'échec de l'IA pour moderation (%),100.0", content)
        self.assertNotIn("{", content)

    def test_menu_links_depend_on_the_role(self):
        for role, expected in (
            (User.Role.ADMIN, {"Pilotage", "Analytics IA"}),
            (User.Role.ETABLISSEMENT, {"Pilotage"}),
            (User.Role.MENTOR, set()),
            (User.Role.APPRENANT, set()),
        ):
            with self.subTest(role=role):
                self.client.force_login(UserFactory(role=role))
                labels = {link["label"] for link in self.client.get("/").context["nav_links"]}
                self.assertEqual(labels & {"Pilotage", "Analytics IA"}, expected)

    def test_learner_reaches_pilotage_from_the_dashboard(self):
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))

        response = self.client.get("/")

        self.assertContains(response, "Mes indicateurs")
        self.assertContains(response, f'href="{reverse("pilotage")}"')
