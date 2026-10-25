from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from payments.models import Invoice, Payment, Plan, Subscription
from payments.services import expire_subscriptions, has_active_subscription, simulate_payment


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.plan = Plan.objects.create(
            name="Premium", slug="premium", price=Decimal("29.900"), duration_days=30
        )

    def test_successful_payment_creates_subscription_and_invoice(self):
        payment = simulate_payment(self.user, self.plan)

        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertTrue(has_active_subscription(self.user))
        invoice = Invoice.objects.get(payment=payment)
        self.assertTrue(invoice.pdf.name)
        self.assertGreater(invoice.pdf.size, 0)

    def test_failed_payment_does_not_create_subscription(self):
        payment = simulate_payment(self.user, self.plan, succeeded=False)

        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertFalse(has_active_subscription(self.user))
        self.assertFalse(Invoice.objects.filter(payment=payment).exists())

    def test_expired_subscription_is_not_active(self):
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            starts_at=timezone.now() - timedelta(days=31),
            ends_at=timezone.now() - timedelta(days=1),
        )

        self.assertFalse(has_active_subscription(self.user))
        self.assertEqual(expire_subscriptions(), 1)
        self.assertEqual(
            Subscription.objects.get(user=self.user).status, Subscription.Status.EXPIRED
        )

    def test_anonymous_user_has_no_active_subscription(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(has_active_subscription(AnonymousUser()))
