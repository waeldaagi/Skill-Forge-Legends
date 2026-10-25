from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from accounts.tests.factories import UserFactory
from mentoring import services
from mentoring.models import MentoringSession
from mentoring.services import (
    CancellationTooLate,
    InvalidSessionStatus,
    ReviewNotAllowed,
    SlotLocked,
    SlotUnavailable,
)
from mentoring.tasks import send_session_reminder
from mentoring.tests.factories import (
    AvailabilitySlotFactory,
    MentoringSessionFactory,
    MentorProfileFactory,
    SessionReviewFactory,
)

Status = MentoringSession.Status


def from_now(**delta):
    return timezone.now() + timedelta(**delta)


class BookSlotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = UserFactory(role=User.Role.APPRENANT)

    def book(self, slot, learner=None):
        return services.book_slot(
            learner or self.learner, slot, "Migrations en conflit", "Deux branches ont créé 0004."
        )

    def test_booking_creates_a_requested_session_and_locks_the_slot(self):
        slot = AvailabilitySlotFactory()

        session = self.book(slot)

        slot.refresh_from_db()
        self.assertTrue(slot.is_booked)
        self.assertEqual(session.status, Status.DEMANDEE)
        self.assertEqual(session.learner, self.learner)

    def test_both_participants_are_emailed_once_the_booking_commits(self):
        slot = AvailabilitySlotFactory()

        with self.captureOnCommitCallbacks(execute=True):
            self.book(slot)

        recipients = sorted(message.to[0] for message in mail.outbox)
        self.assertEqual(recipients, sorted([slot.mentor.email, self.learner.email]))

    def test_learner_cannot_book_an_already_booked_slot(self):
        slot = AvailabilitySlotFactory()
        self.book(slot)

        with self.assertRaises(SlotUnavailable):
            self.book(slot, learner=UserFactory(role=User.Role.APPRENANT))

        self.assertEqual(slot.sessions.count(), 1)

    def test_stale_slot_object_cannot_bypass_the_lock(self):
        slot = AvailabilitySlotFactory()
        stale_copy = type(slot).objects.get(pk=slot.pk)
        self.book(slot)

        with self.assertRaises(SlotUnavailable):
            self.book(stale_copy, learner=UserFactory(role=User.Role.APPRENANT))

    def test_slot_that_already_started_cannot_be_booked(self):
        slot = AvailabilitySlotFactory(start=from_now(minutes=-5), end=from_now(minutes=55))

        with self.assertRaises(SlotUnavailable):
            self.book(slot)


class SessionLifecycleTests(TestCase):
    def test_mentor_confirms_a_requested_session_and_the_learner_is_told(self):
        session = MentoringSessionFactory()

        with self.captureOnCommitCallbacks(execute=True):
            services.confirm_session(session)

        self.assertEqual(session.status, Status.CONFIRMEE)
        self.assertIn("Session confirmée", [message.subject for message in mail.outbox])

    def test_confirmation_schedules_the_reminder_one_hour_before(self):
        session = MentoringSessionFactory()

        with self.captureOnCommitCallbacks(execute=True):
            services.confirm_session(session)

        self.assertTrue(any(message.subject.startswith("Rappel") for message in mail.outbox))

    def test_no_reminder_when_the_session_starts_within_the_hour(self):
        session = MentoringSessionFactory(
            slot__start=from_now(minutes=40), slot__end=from_now(minutes=100)
        )

        with self.captureOnCommitCallbacks(execute=True):
            services.confirm_session(session)

        self.assertFalse(any(message.subject.startswith("Rappel") for message in mail.outbox))

    def test_only_a_requested_session_can_be_confirmed(self):
        session = MentoringSessionFactory(status=Status.ANNULEE)

        with self.assertRaisesMessage(InvalidSessionStatus, "annulée"):
            services.confirm_session(session)

    def test_refusal_keeps_the_mentor_notes_and_frees_the_slot(self):
        session = MentoringSessionFactory()

        services.refuse_session(session, "Je ne connais pas assez Flask pour vous aider.")

        session.slot.refresh_from_db()
        self.assertEqual(session.status, Status.REFUSEE)
        self.assertFalse(session.slot.is_booked)
        self.assertIn("Flask", session.mentor_notes)

    def test_freed_slot_can_be_booked_again(self):
        session = MentoringSessionFactory()
        services.refuse_session(session, "Indisponible.")

        new_session = services.book_slot(
            UserFactory(role=User.Role.APPRENANT), session.slot, "Docker", "Le conteneur redémarre."
        )

        self.assertEqual(new_session.slot, session.slot)

    def test_session_cannot_be_completed_before_it_starts(self):
        session = MentoringSessionFactory(status=Status.CONFIRMEE)

        with self.assertRaises(InvalidSessionStatus):
            services.complete_session(session, "")

    def test_mentor_completes_a_started_session_with_notes(self):
        session = MentoringSessionFactory(
            status=Status.CONFIRMEE,
            slot__start=from_now(minutes=-50),
            slot__end=from_now(minutes=10),
        )

        services.complete_session(session, "Revoir les namespaces d'URL.")

        self.assertEqual(session.status, Status.TERMINEE)
        self.assertEqual(session.mentor_notes, "Revoir les namespaces d'URL.")


class CancellationTests(TestCase):
    def session_starting_in(self, **delta):
        return MentoringSessionFactory(
            status=Status.CONFIRMEE,
            slot__start=from_now(**delta),
            slot__end=from_now(**delta) + timedelta(hours=1),
        )

    def test_learner_can_cancel_2_h_01_before_the_start(self):
        session = self.session_starting_in(hours=2, minutes=1)

        services.cancel_session(session)

        session.slot.refresh_from_db()
        self.assertEqual(session.status, Status.ANNULEE)
        self.assertFalse(session.slot.is_booked)

    def test_learner_cannot_cancel_1_h_59_before_the_start(self):
        session = self.session_starting_in(hours=1, minutes=59)

        with self.assertRaises(CancellationTooLate):
            services.cancel_session(session)

        self.assertEqual(session.status, Status.CONFIRMEE)

    def test_completed_session_cannot_be_cancelled(self):
        session = MentoringSessionFactory(status=Status.TERMINEE)

        with self.assertRaises(InvalidSessionStatus):
            services.cancel_session(session)


class ReviewTests(TestCase):
    def test_learner_reviews_a_completed_session(self):
        session = MentoringSessionFactory(status=Status.TERMINEE)

        review = services.add_review(session, 4, "Bonne explication de select_related.")

        self.assertEqual(review.rating, 4)

    def test_review_before_the_end_is_refused(self):
        session = MentoringSessionFactory(status=Status.CONFIRMEE)

        with self.assertRaises(ReviewNotAllowed):
            services.add_review(session, 5, "")

    def test_second_review_on_the_same_session_is_refused(self):
        review = SessionReviewFactory()

        with self.assertRaisesMessage(ReviewNotAllowed, "déjà"):
            services.add_review(review.session, 3, "")


class RoomWindowTests(TestCase):
    def session(self, status=Status.CONFIRMEE, **delta):
        return MentoringSessionFactory(
            status=status,
            slot__start=from_now(**delta),
            slot__end=from_now(**delta) + timedelta(hours=1),
        )

    def test_room_opens_15_minutes_before_a_confirmed_session(self):
        self.assertTrue(services.room_is_open(self.session(minutes=10)))

    def test_room_is_closed_20_minutes_before(self):
        self.assertFalse(services.room_is_open(self.session(minutes=20)))

    def test_room_stays_closed_for_an_unconfirmed_session(self):
        self.assertFalse(services.room_is_open(self.session(status=Status.DEMANDEE, minutes=5)))

    def test_room_closes_at_the_end_of_the_session(self):
        self.assertFalse(services.room_is_open(self.session(minutes=-61)))


class DirectoryAndSlotTests(TestCase):
    def test_directory_computes_the_average_rating_of_each_mentor(self):
        profile = MentorProfileFactory()
        for rating in (5, 4):
            SessionReviewFactory(rating=rating, session__slot__mentor=profile.mentor)

        listed = services.mentor_directory().get(pk=profile.pk)

        self.assertEqual(listed.average_rating, 4.5)
        self.assertEqual(listed.review_count, 2)

    def test_free_slots_exclude_booked_and_past_slots(self):
        free = AvailabilitySlotFactory()
        AvailabilitySlotFactory(mentor=free.mentor, is_booked=True, start=from_now(days=4))
        AvailabilitySlotFactory(
            mentor=free.mentor, start=from_now(days=-1), end=from_now(days=-1, hours=1)
        )

        self.assertEqual(list(services.free_slots(free.mentor)), [free])

    def test_booked_slot_is_locked_for_editing(self):
        with self.assertRaises(SlotLocked):
            services.ensure_slot_editable(AvailabilitySlotFactory(is_booked=True))


class ReminderTaskTests(TestCase):
    def test_reminder_is_skipped_when_the_session_was_cancelled(self):
        session = MentoringSessionFactory(status=Status.ANNULEE)

        send_session_reminder(session.pk)

        self.assertEqual(mail.outbox, [])

    def test_reminder_reaches_both_participants(self):
        session = MentoringSessionFactory(status=Status.CONFIRMEE)

        send_session_reminder(session.pk)

        self.assertCountEqual(mail.outbox[0].to, [session.learner.email, session.mentor.email])
