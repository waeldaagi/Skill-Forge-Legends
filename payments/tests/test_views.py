from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from payments.models import Payment, Plan, Subscription
from payments.services import simulate_payment


class PaymentViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.plan = Plan.objects.create(
            name="Premium", slug="premium", price=Decimal("29.900"), duration_days=30
        )

    def test_plan_list_is_public(self):
        response = self.client.get(reverse("payments:plans"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium")

    def test_authenticated_user_sees_subscription_icon_in_top_bar(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("payments:plans"))

        self.assertContains(response, 'href="/paiements/"')
        self.assertContains(response, "bi-credit-card-2-front")

    def test_checkout_requires_login(self):
        response = self.client.post(reverse("payments:checkout", args=[self.plan.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Payment.objects.count(), 0)

    def test_successful_checkout_creates_payment_for_logged_in_user(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("payments:checkout", args=[self.plan.slug]))

        self.assertRedirects(response, reverse("payments:subscriptions"))
        self.assertTrue(
            Payment.objects.filter(user=self.user, status=Payment.Status.SUCCEEDED).exists()
        )

    def test_active_plan_shows_cancel_instead_of_pay(self):
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=30),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("payments:plans"))

        self.assertContains(response, "Annuler")
        self.assertContains(response, "Abonnement actif")
        self.assertNotContains(response, "Payer (mode démo)")

    def test_user_can_only_cancel_own_subscription(self):
        subscription = Subscription.objects.create(
            user=self.other_user,
            plan=self.plan,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=30),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse("payments:cancel", args=[subscription.pk]))

        self.assertEqual(response.status_code, 404)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)

    def test_cancelling_removes_subscription_and_restores_pay_button(self):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=30),
        )
        self.client.force_login(self.user)

        cancel_response = self.client.post(reverse("payments:cancel", args=[subscription.pk]))
        subscriptions_response = self.client.get(reverse("payments:subscriptions"))
        plans_response = self.client.get(reverse("payments:plans"))

        self.assertRedirects(cancel_response, reverse("payments:subscriptions"))
        self.assertNotContains(subscriptions_response, self.plan.name)
        self.assertContains(plans_response, "Payer")
        self.assertNotContains(plans_response, "Abonnement actif")

    def test_second_checkout_does_not_stack_active_subscriptions(self):
        self.client.force_login(self.user)
        checkout_url = reverse("payments:checkout", args=[self.plan.slug])

        self.client.post(checkout_url)
        self.client.post(checkout_url)

        self.assertEqual(
            Subscription.objects.filter(
                user=self.user, plan=self.plan, status=Subscription.Status.ACTIVE
            ).count(),
            1,
        )

    def test_owner_can_download_invoice_pdf(self):
        payment = simulate_payment(self.user, self.plan)
        self.client.force_login(self.user)

        response = self.client.get(reverse("payments:invoice_download", args=[payment.invoice.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_download_generates_missing_pdf_for_old_invoice(self):
        payment = simulate_payment(self.user, self.plan)
        payment.invoice.pdf.delete(save=True)
        self.client.force_login(self.user)

        response = self.client.get(reverse("payments:invoice_download", args=[payment.invoice.pk]))

        self.assertEqual(response.status_code, 200)
        payment.invoice.refresh_from_db()
        self.assertTrue(payment.invoice.pdf.name)

    def test_payment_page_shows_only_latest_successful_payment_per_plan(self):
        simulate_payment(self.user, self.plan)
        first_payment = Payment.objects.filter(user=self.user).first()
        first_payment.created_at = timezone.now() - timedelta(days=1)
        first_payment.save(update_fields=["created_at"])
        simulate_payment(self.user, self.plan)
        self.client.force_login(self.user)

        response = self.client.get(reverse("payments:payments"))

        self.assertEqual(len(response.context["payments"]), 1)
        self.assertEqual(
            response.context["payments"][0].pk,
            Payment.objects.latest("created_at").pk,
        )

    def test_payment_page_is_empty_after_subscription_cancellation(self):
        payment = simulate_payment(self.user, self.plan)
        subscription = Subscription.objects.get(
            user=self.user, plan=self.plan, status=Subscription.Status.ACTIVE
        )
        self.client.force_login(self.user)
        self.client.post(reverse("payments:cancel", args=[subscription.pk]))

        response = self.client.get(reverse("payments:payments"))

        self.assertEqual(len(response.context["payments"]), 0)
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())

    def test_user_cannot_download_another_users_invoice(self):
        payment = simulate_payment(self.other_user, self.plan)
        self.client.force_login(self.user)

        response = self.client.get(reverse("payments:invoice_download", args=[payment.invoice.pk]))

        self.assertEqual(response.status_code, 404)


class PaymentScenarioTests(TestCase):
    def test_plan_page_offers_the_refused_payment_scenario(self):
        Plan.objects.create(name="Premium", slug="premium", price="29.900", duration_days=30)
        self.client.force_login(UserFactory())

        response = self.client.get(reverse("payments:plans"))

        self.assertContains(response, 'name="scenario" value="failure"')

    def test_refused_payment_creates_no_subscription(self):
        plan = Plan.objects.create(name="Premium", slug="premium", price="29.900", duration_days=30)
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.post(
            reverse("payments:checkout", args=[plan.slug]), {"scenario": "failure"}, follow=True
        )

        self.assertContains(response, "Le paiement de démonstration a échoué.")
        self.assertFalse(Subscription.objects.filter(user=user).exists())
