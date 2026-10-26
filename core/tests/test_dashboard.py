"""Accueil d'un utilisateur connecté : les panneaux que chaque app déclare pour son rôle."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from community.models import ModerationStatus
from community.tests.factories import ThreadFactory
from courses.services import mark_chapter_completed
from courses.tests.factories import ChapterFactory, CourseFactory, QuizFactory, TrainerFactory
from mentoring.models import SessionStatus
from mentoring.tests.factories import (
    AvailabilitySlotFactory,
    MentoringSessionFactory,
    MentorProfileFactory,
)


class DashboardTests(TestCase):
    def home(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("core:home"))

    def test_visitor_sees_the_presentation(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "Le parcours d'un apprenant")
        self.assertNotIn("panels", response.context)

    def test_learner_sees_course_progress_and_next_session(self):
        learner = UserFactory(role=User.Role.APPRENANT)
        first = ChapterFactory(order=1, course__title="Docker pour développeurs")
        ChapterFactory(course=first.course, order=2)
        mark_chapter_completed(learner, first)
        session = MentoringSessionFactory(learner=learner, status=SessionStatus.CONFIRMEE)

        response = self.home(learner)

        self.assertContains(response, "Bonjour")
        self.assertContains(response, "Docker pour développeurs</a> · 50 %")
        self.assertContains(response, reverse("mentoring:session_detail", args=[session.pk]))
        self.assertNotContains(response, "Le parcours d'un apprenant")

    def test_learner_without_course_is_sent_to_the_catalogue(self):
        response = self.home(UserFactory(role=User.Role.APPRENANT))

        self.assertContains(response, "Vous ne suivez encore aucun cours")
        self.assertContains(response, "Aucune session prévue")

    def test_trainer_sees_course_and_quiz_counts(self):
        trainer = TrainerFactory()
        CourseFactory(trainer=trainer)
        QuizFactory(
            chapter__course__trainer=trainer, chapter__course__status="DRAFT", is_published=False
        )

        panel = next(p for p in self.home(trainer).context["panels"] if "draft_count" in p)

        self.assertEqual(
            (panel["published_count"], panel["draft_count"], panel["draft_quiz_count"]), (1, 1, 1)
        )

    def test_mentor_sees_pending_requests_and_free_slots(self):
        profile = MentorProfileFactory()
        MentoringSessionFactory(slot__mentor=profile.mentor)
        AvailabilitySlotFactory(mentor=profile.mentor)

        response = self.home(profile.mentor)

        panel = next(
            p for p in response.context["panels"] if "pending_count" in p and "has_profile" in p
        )
        self.assertEqual((panel["pending_count"], panel["free_slot_count"]), (1, 1))
        self.assertNotContains(response, "complétez votre profil de mentor")

    def test_unverified_mentor_is_warned(self):
        response = self.home(UserFactory(role=User.Role.MENTOR, is_verified=False))

        self.assertContains(response, "vos créneaux ne sont pas publiés")

    def test_moderators_see_the_number_of_items_to_review(self):
        ThreadFactory(moderation_status=ModerationStatus.SIGNALE)

        for role in (User.Role.MENTOR, User.Role.ADMIN):
            with self.subTest(role=role):
                response = self.home(UserFactory(role=role, is_verified=True))
                self.assertContains(response, "1 élément attend une décision")

    def test_role_without_panel_is_sent_to_its_profile(self):
        response = self.home(UserFactory(role=User.Role.RECRUTEUR))

        self.assertEqual(response.context["panels"], [])
        self.assertContains(response, reverse("accounts:profile_edit"))
