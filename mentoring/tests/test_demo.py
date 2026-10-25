from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import User
from mentoring import services
from mentoring.demo import LIVE_SESSION_TOPIC
from mentoring.models import AvailabilitySlot, MentoringSession


@override_settings(DEMO_PASSWORD="Demo-Soutenance-2026")
class MentoringDemoDataTests(TestCase):
    def seed(self):
        call_command("seed_demo", stdout=StringIO())

    def test_demo_shows_every_step_of_a_session(self):
        self.seed()

        statuses = set(MentoringSession.objects.values_list("status", flat=True))
        self.assertTrue(
            {"DEMANDEE", "CONFIRMEE", "TERMINEE"} <= statuses, f"statuts présents : {statuses}"
        )

    def test_demo_mentor_has_a_request_to_answer(self):
        self.seed()

        mentor = User.objects.get(username="skander.jaziri")
        self.assertTrue(
            MentoringSession.objects.filter(
                slot__mentor=mentor, status=MentoringSession.Status.DEMANDEE
            ).exists()
        )

    def test_live_session_room_is_open_right_after_seeding(self):
        self.seed()

        live = MentoringSession.objects.get(topic=LIVE_SESSION_TOPIC)
        self.assertTrue(services.room_is_open(live))
        self.assertEqual(live.status, MentoringSession.Status.CONFIRMEE)

    def test_seeding_twice_keeps_the_same_slots_and_sessions(self):
        self.seed()
        counts = (AvailabilitySlot.objects.count(), MentoringSession.objects.count())

        self.seed()

        self.assertEqual(
            (AvailabilitySlot.objects.count(), MentoringSession.objects.count()), counts
        )
