from datetime import timedelta

from django.contrib.messages import get_messages
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import Skill, User
from accounts.tests.factories import UserFactory
from courses.services import enroll_learner
from courses.tests.factories import CourseFactory
from mentoring.forms import DATETIME_LOCAL_FORMAT
from mentoring.models import AvailabilitySlot, MentoringSession, MentorProfile, SessionReview
from mentoring.tests.factories import (
    AvailabilitySlotFactory,
    MentoringSessionFactory,
    MentorProfileFactory,
    SessionReviewFactory,
    in_days,
)

Status = MentoringSession.Status


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def local(moment):
    return timezone.localtime(moment).strftime(DATETIME_LOCAL_FORMAT)


def from_now(**delta):
    return timezone.now() + timedelta(**delta)


class MentorProfileViewTests(TestCase):
    def setUp(self):
        self.mentor = UserFactory(role=User.Role.MENTOR)
        self.client.force_login(self.mentor)
        self.url = reverse("mentoring:profile_edit")

    def test_first_save_creates_the_profile(self):
        response = self.client.post(
            self.url, {"title": "Développeur back-end Django", "years_of_experience": 6}
        )

        self.assertRedirects(response, reverse("mentoring:slot_list"))
        self.assertEqual(MentorProfile.objects.get(mentor=self.mentor).years_of_experience, 6)

    def test_next_save_updates_the_same_profile(self):
        MentorProfileFactory(mentor=self.mentor)

        self.client.post(self.url, {"title": "Ingénieur DevOps", "years_of_experience": 8})

        self.assertEqual(MentorProfile.objects.filter(mentor=self.mentor).count(), 1)
        self.assertEqual(MentorProfile.objects.get(mentor=self.mentor).title, "Ingénieur DevOps")


class SlotViewsTests(TestCase):
    def setUp(self):
        self.mentor = UserFactory(role=User.Role.MENTOR, is_verified=True)
        self.client.force_login(self.mentor)

    def test_list_shows_only_my_upcoming_slots(self):
        mine = AvailabilitySlotFactory(mentor=self.mentor)
        AvailabilitySlotFactory()

        response = self.client.get(reverse("mentoring:slot_list"))

        self.assertTemplateUsed(response, "mentoring/slot_list.html")
        self.assertEqual(list(response.context["slots"]), [mine])
        self.assertFalse(response.context["has_profile"])

    def test_list_filters_free_slots(self):
        free = AvailabilitySlotFactory(mentor=self.mentor)
        AvailabilitySlotFactory(mentor=self.mentor, is_booked=True, start=in_days(5))

        response = self.client.get(reverse("mentoring:slot_list"), {"etat": "libres"})

        self.assertEqual(list(response.context["slots"]), [free])

    def test_creating_a_slot_assigns_it_to_me(self):
        start = in_days(4)

        response = self.client.post(
            reverse("mentoring:slot_create"),
            {"start": local(start), "end": local(start + timedelta(minutes=90))},
        )

        self.assertRedirects(response, reverse("mentoring:slot_list"))
        slot = AvailabilitySlot.objects.get()
        self.assertEqual(slot.mentor, self.mentor)
        self.assertIn("Créneau ajouté", messages_of(response)[0])

    def test_overlapping_slot_is_refused_with_its_reason(self):
        AvailabilitySlotFactory(mentor=self.mentor, start=in_days(4))

        response = self.client.post(
            reverse("mentoring:slot_create"),
            {"start": local(in_days(4)), "end": local(in_days(4) + timedelta(hours=1))},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "chevauche")
        self.assertEqual(AvailabilitySlot.objects.count(), 1)

    def test_free_slot_can_be_moved(self):
        slot = AvailabilitySlotFactory(mentor=self.mentor)
        new_start = in_days(6, hour=9)

        self.client.post(
            reverse("mentoring:slot_update", args=[slot.pk]),
            {"start": local(new_start), "end": local(new_start + timedelta(hours=1))},
        )

        slot.refresh_from_db()
        self.assertEqual(slot.start, new_start)

    def test_booked_slot_cannot_be_edited_and_the_page_says_why(self):
        slot = AvailabilitySlotFactory(mentor=self.mentor, is_booked=True)

        response = self.client.get(reverse("mentoring:slot_update", args=[slot.pk]))

        self.assertContains(response, "plus modifiable", status_code=403)

    def test_free_slot_can_be_deleted(self):
        slot = AvailabilitySlotFactory(mentor=self.mentor)

        response = self.client.post(reverse("mentoring:slot_delete", args=[slot.pk]))

        self.assertRedirects(response, reverse("mentoring:slot_list"))
        self.assertFalse(AvailabilitySlot.objects.exists())

    def test_booked_slot_cannot_be_deleted(self):
        slot = AvailabilitySlotFactory(mentor=self.mentor, is_booked=True)

        response = self.client.post(reverse("mentoring:slot_delete", args=[slot.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(AvailabilitySlot.objects.filter(pk=slot.pk).exists())

    def test_list_shows_past_slots_on_request(self):
        past = AvailabilitySlotFactory(
            mentor=self.mentor, start=from_now(days=-2), end=from_now(days=-2, hours=1)
        )
        AvailabilitySlotFactory(mentor=self.mentor)

        response = self.client.get(reverse("mentoring:slot_list"), {"periode": "passes"})

        self.assertEqual(list(response.context["slots"]), [past])

    def test_list_filters_booked_slots(self):
        booked = AvailabilitySlotFactory(mentor=self.mentor, is_booked=True)
        AvailabilitySlotFactory(mentor=self.mentor, start=in_days(5))

        response = self.client.get(reverse("mentoring:slot_list"), {"etat": "reserves"})

        self.assertEqual(list(response.context["slots"]), [booked])

    def test_next_page_link_keeps_the_filter(self):
        for day in range(1, 13):
            AvailabilitySlotFactory(mentor=self.mentor, start=in_days(day))

        response = self.client.get(reverse("mentoring:slot_list"), {"etat": "libres"})

        self.assertContains(response, 'href="?etat=libres&amp;page=2"')

    def test_unverified_mentor_cannot_add_a_slot_and_is_told_why(self):
        self.client.force_login(UserFactory(role=User.Role.MENTOR, is_verified=False))

        response = self.client.get(reverse("mentoring:slot_create"))

        self.assertContains(response, "doit être vérifié", status_code=403)

    def test_slot_list_warns_an_unverified_mentor(self):
        self.client.force_login(UserFactory(role=User.Role.MENTOR, is_verified=False))

        response = self.client.get(reverse("mentoring:slot_list"))

        self.assertContains(response, "pas encore vérifié")
        self.assertNotContains(response, reverse("mentoring:slot_create"))


class DirectoryViewsTests(TestCase):
    def setUp(self):
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))

    def test_directory_lists_mentors_with_their_rating(self):
        profile = MentorProfileFactory()
        SessionReviewFactory(rating=4, session__slot__mentor=profile.mentor)

        response = self.client.get(reverse("mentoring:mentor_directory"))

        self.assertTemplateUsed(response, "mentoring/mentor_directory.html")
        self.assertContains(response, "4,0/5 sur 1 avis")

    def test_search_matches_the_specialty(self):
        devops = MentorProfileFactory(title="Ingénieure DevOps, Docker et CI")
        MentorProfileFactory(title="Développeur front-end")

        response = self.client.get(reverse("mentoring:mentor_directory"), {"q": "docker"})

        self.assertEqual(list(response.context["profiles"]), [devops])

    def test_available_filter_hides_mentors_without_free_slots(self):
        available = MentorProfileFactory()
        AvailabilitySlotFactory(mentor=available.mentor)
        MentorProfileFactory()

        response = self.client.get(reverse("mentoring:mentor_directory"), {"disponible": "on"})

        self.assertEqual(list(response.context["profiles"]), [available])

    def test_directory_query_count_does_not_grow_with_the_number_of_mentors(self):
        MentorProfileFactory()
        with CaptureQueriesContext(connection) as one_mentor:
            self.client.get(reverse("mentoring:mentor_directory"))
        for _ in range(4):
            AvailabilitySlotFactory(mentor=MentorProfileFactory().mentor)

        with CaptureQueriesContext(connection) as five_mentors:
            self.client.get(reverse("mentoring:mentor_directory"))

        self.assertEqual(len(five_mentors), len(one_mentor))

    def test_mentor_page_lists_only_free_upcoming_slots(self):
        profile = MentorProfileFactory()
        free = AvailabilitySlotFactory(mentor=profile.mentor)
        AvailabilitySlotFactory(mentor=profile.mentor, is_booked=True, start=in_days(5))

        response = self.client.get(reverse("mentoring:mentor_detail", args=[profile.pk]))

        self.assertEqual(list(response.context["free_slots"]), [free])

    def test_directory_filters_on_an_expertise(self):
        docker = Skill.objects.create(name="Docker")
        devops = MentorProfileFactory()
        devops.expertises.add(docker)
        MentorProfileFactory()

        response = self.client.get(reverse("mentoring:mentor_directory"), {"expertise": docker.pk})

        self.assertEqual(list(response.context["profiles"]), [devops])
        self.assertContains(response, "Expertises&nbsp;: Docker")


class BookingViewTests(TestCase):
    def setUp(self):
        self.learner = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(self.learner)
        self.slot = AvailabilitySlotFactory()
        self.url = reverse("mentoring:slot_book", args=[self.slot.pk])

    def test_booking_form_shows_the_slot(self):
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "mentoring/slot_book.html")
        self.assertEqual(response.context["slot"], self.slot)

    def test_booking_creates_the_session_and_opens_it(self):
        response = self.client.post(
            self.url, {"topic": "Tests Django", "blocker_description": "Mon TestCase échoue."}
        )

        session = MentoringSession.objects.get()
        self.assertRedirects(response, reverse("mentoring:session_detail", args=[session.pk]))
        self.assertEqual(session.learner, self.learner)

    def test_booked_slot_sends_the_learner_back_to_the_directory(self):
        self.slot.is_booked = True
        self.slot.save()

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("mentoring:mentor_directory"))
        self.assertIn("plus disponible", messages_of(response)[0])

    def test_slot_taken_while_filling_the_form_is_reported(self):
        MentoringSessionFactory(slot=self.slot)
        self.slot.is_booked = True
        self.slot.save()

        response = self.client.post(
            self.url, {"topic": "Tests Django", "blocker_description": "Mon TestCase échoue."}
        )

        self.assertRedirects(response, reverse("mentoring:mentor_directory"))
        self.assertIn("vient d'être réservé", messages_of(response)[0])

    def test_booking_offers_only_my_courses_and_keeps_the_choice(self):
        mine = CourseFactory()
        CourseFactory()  # cours auquel l'apprenant n'est pas inscrit
        enroll_learner(self.learner, mine)

        form = self.client.get(self.url).context["form"]
        self.client.post(
            self.url,
            {"topic": "Tests Django", "blocker_description": "Mon test échoue.", "course": mine.pk},
        )

        self.assertEqual(list(form.fields["course"].queryset), [mine])
        self.assertEqual(MentoringSession.objects.get().course, mine)

    def test_slot_of_an_unverified_mentor_is_not_offered(self):
        slot = AvailabilitySlotFactory(mentor__is_verified=False)

        response = self.client.get(reverse("mentoring:slot_book", args=[slot.pk]))

        self.assertRedirects(response, reverse("mentoring:mentor_directory"))


class SessionViewsTests(TestCase):
    def setUp(self):
        self.session = MentoringSessionFactory()
        self.learner = self.session.learner
        self.mentor = self.session.slot.mentor

    def url(self, name):
        return reverse(f"mentoring:{name}", args=[self.session.pk])

    def test_each_participant_sees_the_session_in_their_list(self):
        MentoringSessionFactory()
        for participant in (self.learner, self.mentor):
            with self.subTest(participant=participant.role):
                self.client.force_login(participant)
                response = self.client.get(reverse("mentoring:session_list"))
                self.assertEqual(list(response.context["sessions"]), [self.session])

    def test_list_filters_by_status(self):
        self.client.force_login(self.learner)

        response = self.client.get(reverse("mentoring:session_list"), {"statut": "CONFIRMEE"})

        self.assertEqual(list(response.context["sessions"]), [])

    def test_mentor_is_offered_to_answer_a_request(self):
        self.client.force_login(self.mentor)

        response = self.client.get(self.url("session_detail"))

        self.assertTrue(response.context["can_answer"])
        self.assertFalse(response.context["can_cancel"])

    def test_learner_is_offered_to_cancel_a_request(self):
        self.client.force_login(self.learner)

        response = self.client.get(self.url("session_detail"))

        self.assertTrue(response.context["can_cancel"])
        self.assertFalse(response.context["can_answer"])

    def test_mentor_confirms_with_a_post(self):
        self.client.force_login(self.mentor)

        response = self.client.post(self.url("session_confirm"))

        self.assertRedirects(response, self.url("session_detail"))
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, Status.CONFIRMEE)

    def test_confirmation_by_get_is_not_allowed(self):
        self.client.force_login(self.mentor)

        self.assertEqual(self.client.get(self.url("session_confirm")).status_code, 405)

    def test_refusal_without_reason_shows_the_form_again(self):
        self.client.force_login(self.mentor)

        response = self.client.post(self.url("session_refuse"), {"mentor_notes": ""})

        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, Status.DEMANDEE)

    def test_refusal_with_reason_frees_the_slot(self):
        self.client.force_login(self.mentor)

        self.client.post(self.url("session_refuse"), {"mentor_notes": "Je suis en congé."})

        self.session.refresh_from_db()
        self.assertEqual(self.session.status, Status.REFUSEE)
        self.assertFalse(self.session.slot.is_booked)

    def test_completing_before_the_start_explains_the_refusal(self):
        self.session.status = Status.CONFIRMEE
        self.session.save()
        self.client.force_login(self.mentor)

        response = self.client.post(self.url("session_complete"), {"mentor_notes": ""})

        self.assertIn("après son début", messages_of(response)[0])
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, Status.CONFIRMEE)

    def test_learner_cancels_after_confirming(self):
        self.client.force_login(self.learner)

        confirmation = self.client.get(self.url("session_cancel"))
        response = self.client.post(self.url("session_cancel"))

        self.assertContains(confirmation, "le créneau redeviendra libre")
        self.assertRedirects(response, self.url("session_detail"))
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, Status.ANNULEE)

    def test_late_cancellation_is_refused_with_its_reason(self):
        self.session.slot.start = from_now(hours=1)
        self.session.slot.end = from_now(hours=2)
        self.session.slot.save()
        self.client.force_login(self.learner)

        response = self.client.post(self.url("session_cancel"))

        self.assertIn("moins de 2 h", messages_of(response)[0])

    def test_learner_reviews_a_completed_session(self):
        self.session.status = Status.TERMINEE
        self.session.save()
        self.client.force_login(self.learner)

        self.client.post(self.url("session_review"), {"rating": "5", "comment": "Très utile."})

        self.assertEqual(SessionReview.objects.get(session=self.session).rating, 5)

    def test_list_separates_upcoming_and_past_sessions(self):
        past = MentoringSessionFactory(
            learner=self.learner,
            status=Status.TERMINEE,
            slot__start=from_now(days=-3),
            slot__end=from_now(days=-3, hours=1),
        )
        self.client.force_login(self.learner)

        upcoming = self.client.get(reverse("mentoring:session_list"), {"periode": "a_venir"})
        finished = self.client.get(reverse("mentoring:session_list"), {"periode": "passees"})

        self.assertEqual(list(upcoming.context["sessions"]), [self.session])
        self.assertEqual(list(finished.context["sessions"]), [past])


class RoomViewTests(TestCase):
    def session_starting_in(self, **delta):
        return MentoringSessionFactory(
            status=Status.CONFIRMEE,
            slot__start=from_now(**delta),
            slot__end=from_now(**delta) + timedelta(hours=1),
        )

    def test_open_room_embeds_jitsi_with_an_accessible_title(self):
        session = self.session_starting_in(minutes=10)
        self.client.force_login(session.learner)

        response = self.client.get(reverse("mentoring:session_room", args=[session.pk]))

        self.assertTemplateUsed(response, "mentoring/session_room.html")
        self.assertContains(response, f'src="{session.jitsi_url}"')
        self.assertContains(response, 'title="Visioconférence Jitsi de la session')

    def test_closed_room_explains_when_it_opens(self):
        session = self.session_starting_in(hours=3)
        self.client.force_login(session.slot.mentor)

        response = self.client.get(reverse("mentoring:session_room", args=[session.pk]))

        self.assertContains(response, "15 minutes avant le début", status_code=403)
