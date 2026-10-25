from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from accounts.tests.factories import UserFactory
from mentoring.models import AvailabilitySlot, MentoringSession, MentorProfile
from mentoring.tests.factories import (
    AvailabilitySlotFactory,
    MentoringSessionFactory,
    SessionReviewFactory,
    in_days,
)


class AvailabilitySlotCleanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mentor = UserFactory(role=User.Role.MENTOR)

    def build(self, start, duration):
        return AvailabilitySlot(mentor=self.mentor, start=start, end=start + duration)

    def test_valid_one_hour_slot_passes(self):
        self.build(in_days(2), timedelta(hours=1)).full_clean()

    def test_end_before_start_is_refused(self):
        slot = self.build(in_days(2), -timedelta(minutes=30))

        with self.assertRaisesMessage(ValidationError, "après son début"):
            slot.full_clean()

    def test_slot_in_the_past_is_refused(self):
        slot = self.build(timezone.now() - timedelta(hours=2), timedelta(hours=1))

        with self.assertRaisesMessage(ValidationError, "dans le futur"):
            slot.full_clean()

    def test_duration_must_stay_between_30_and_120_minutes(self):
        for minutes in (29, 121):
            with (
                self.subTest(minutes=minutes),
                self.assertRaisesMessage(ValidationError, "entre 30 et 120 minutes"),
            ):
                self.build(in_days(2), timedelta(minutes=minutes)).full_clean()

    def test_duration_limits_are_included(self):
        for minutes in (30, 120):
            with self.subTest(minutes=minutes):
                self.build(in_days(2), timedelta(minutes=minutes)).full_clean()

    def test_overlapping_slot_of_the_same_mentor_is_refused(self):
        AvailabilitySlotFactory(mentor=self.mentor, start=in_days(2, hour=14))
        overlapping = self.build(in_days(2, hour=14) + timedelta(minutes=30), timedelta(hours=1))

        with self.assertRaisesMessage(ValidationError, "chevauche"):
            overlapping.full_clean()

    def test_back_to_back_slots_do_not_overlap(self):
        AvailabilitySlotFactory(mentor=self.mentor, start=in_days(2, hour=14))

        self.build(in_days(2, hour=15), timedelta(hours=1)).full_clean()

    def test_another_mentor_may_use_the_same_hours(self):
        AvailabilitySlotFactory(start=in_days(2, hour=14))

        self.build(in_days(2, hour=14), timedelta(hours=1)).full_clean()

    def test_editing_a_slot_does_not_overlap_with_itself(self):
        slot = AvailabilitySlotFactory(mentor=self.mentor, start=in_days(2))
        slot.end = slot.end + timedelta(minutes=30)

        slot.full_clean()

    def test_database_refuses_an_end_before_the_start(self):
        with self.assertRaises(IntegrityError):
            AvailabilitySlotFactory(start=in_days(2), end=in_days(2) - timedelta(hours=1))


class MentoringSessionConstraintTests(TestCase):
    def test_database_refuses_two_active_sessions_on_one_slot(self):
        session = MentoringSessionFactory()

        with self.assertRaises(IntegrityError), transaction.atomic():
            MentoringSessionFactory(slot=session.slot)

    def test_cancelled_session_frees_the_slot_for_a_new_booking(self):
        session = MentoringSessionFactory(status=MentoringSession.Status.ANNULEE)

        MentoringSessionFactory(slot=session.slot)

        self.assertEqual(session.slot.sessions.count(), 2)

    def test_jitsi_room_is_named_after_the_session_uuid(self):
        session = MentoringSessionFactory()

        self.assertEqual(session.jitsi_url, f"https://meet.jit.si/SkillForge-{session.room_name}")


class MentorProfileTests(TestCase):
    def test_only_a_mentor_can_have_a_mentor_profile(self):
        profile = MentorProfile(
            mentor=UserFactory(role=User.Role.APPRENANT), title="Développeur", years_of_experience=3
        )

        with self.assertRaisesMessage(ValidationError, "rôle Mentor"):
            profile.full_clean()


class SessionReviewConstraintTests(TestCase):
    def test_database_refuses_a_rating_outside_1_to_5(self):
        with self.assertRaises(IntegrityError):
            SessionReviewFactory(rating=6)

    def test_str_shows_the_rating(self):
        review = SessionReviewFactory(rating=4)

        self.assertTrue(str(review).startswith("4/5"))
