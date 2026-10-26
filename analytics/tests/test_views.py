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

    def test_dashboard_alias_is_available_at_analytics_path(self):
        self.client.force_login(self.user)

        response = self.client.get("/analytics/")

        self.assertEqual(response.status_code, 200)

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

        self.assertEqual(response.context["chart_data"]["paiements"], 0)
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
        self.client.force_login(self.user)

        response = self.client.get(reverse("analytics:dashboard"))

        self.assertTrue(response.context["dropout"]["available"])
        self.assertGreater(response.context["dropout"]["dropout_rate"], 0)
        self.assertContains(response, "Taux d'abandon")
