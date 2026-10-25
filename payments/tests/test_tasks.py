from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from payments.models import Plan, Subscription
from payments.tasks import expire_subscriptions_task


class PaymentTaskTests(TestCase):
    def test_expiration_task_updates_expired_subscriptions(self):
        user = UserFactory()
        plan = Plan.objects.create(name="Premium", slug="premium", price="29.900", duration_days=30)
        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            starts_at=timezone.now() - timedelta(days=31),
            ends_at=timezone.now() - timedelta(days=1),
        )

        self.assertEqual(expire_subscriptions_task.run(), 1)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.EXPIRED)
