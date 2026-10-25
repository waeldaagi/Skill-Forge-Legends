from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from community import services
from community.models import Reply, Report, Thread


@override_settings(DEMO_PASSWORD="Demo-Soutenance-2026")
class CommunityDemoDataTests(TestCase):
    def seed(self):
        call_command("seed_demo", stdout=StringIO())

    def test_demo_fills_the_moderation_queue(self):
        self.seed()

        queue = services.moderation_queue()
        self.assertTrue(queue["threads"].exists())
        self.assertTrue(queue["replies"].exists())
        self.assertTrue(queue["reports"].exists())

    def test_demo_has_a_resolved_thread_with_an_accepted_reply(self):
        self.seed()

        self.assertTrue(Thread.objects.filter(is_resolved=True, replies__is_accepted=True).exists())

    def test_seeding_twice_duplicates_nothing(self):
        self.seed()
        counts = (Thread.objects.count(), Reply.objects.count(), Report.objects.count())

        self.seed()

        self.assertEqual(
            (Thread.objects.count(), Reply.objects.count(), Report.objects.count()), counts
        )
