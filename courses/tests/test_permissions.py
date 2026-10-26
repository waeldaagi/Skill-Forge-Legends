"""Matrice d'accès des cours : chaque URL, pour chaque rôle et pour un visiteur anonyme.

Le formateur de la matrice ne possède aucun cours : sur le cours d'un autre, il reçoit 404.
docs/modules/courses.md reprend ces règles.
"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from courses.models import Question, Quiz, Resource

from .factories import ChapterFactory, ChoiceFactory

ANONYMOUS = None
Role = User.Role
EVERY_ROLE = set(Role)


def expected(allowed_roles, allowed_status=200, anonymous_status=302):
    statuses = {ANONYMOUS: anonymous_status}
    for role in Role:
        statuses[role] = allowed_status if role in allowed_roles else 403
    return statuses


class CourseAccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.chapter = ChapterFactory()
        cls.course = cls.chapter.course
        cls.quiz = Quiz.objects.create(chapter=cls.chapter, title="Quiz publié", is_published=True)
        cls.question = Question.objects.create(
            quiz=cls.quiz,
            statement="Question",
            explanation="Explication",
            evidence="Extrait",
            order=1,
        )
        ChoiceFactory(question=cls.question, is_correct=True)
        cls.resource = Resource.objects.create(
            chapter=cls.chapter, title="Documentation", url="https://docs.djangoproject.com/"
        )
        cls.users = {role: UserFactory(role=role) for role in Role}

    def check(self, url, statuses, method="get"):
        for role, status in statuses.items():
            with self.subTest(url=url, role=role):
                self.client.logout()
                if role is not ANONYMOUS:
                    self.client.force_login(self.users[role])
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, status)

    def test_catalogue_and_course_detail_are_public(self):
        public = expected(EVERY_ROLE, anonymous_status=200)
        self.check(reverse("courses:list"), public)
        self.check(self.course.get_absolute_url(), public)

    def test_chapters_and_quizzes_of_a_free_course_need_a_session(self):
        members = expected(EVERY_ROLE)
        self.check(reverse("courses:chapter", args=[self.chapter.pk]), members)
        self.check(reverse("courses:quiz", args=[self.quiz.pk]), members)

    def test_only_learners_enroll_complete_a_chapter_or_submit_a_quiz(self):
        learner_action = expected({Role.APPRENANT}, allowed_status=302)
        self.check(reverse("courses:enroll", args=[self.course.slug]), learner_action, "post")
        complete = reverse("courses:complete_chapter", args=[self.chapter.pk])
        self.check(complete, learner_action, "post")
        self.check(reverse("courses:quiz", args=[self.quiz.pk]), learner_action, "post")

    def test_trainer_pages_are_reserved_to_trainers(self):
        trainer_page = expected({Role.FORMATEUR})
        self.check(reverse("courses:create"), trainer_page)
        self.check(reverse("courses:trainer_courses"), trainer_page)

    def test_another_trainers_course_is_not_found(self):
        not_found = expected({Role.FORMATEUR}, allowed_status=404)
        for name, args in (
            ("courses:update", [self.course.slug]),
            ("courses:delete", [self.course.slug]),
            ("courses:chapter_create", [self.course.pk]),
            ("courses:chapter_update", [self.chapter.pk]),
            ("courses:chapter_delete", [self.chapter.pk]),
            ("courses:resource_create", [self.chapter.pk]),
            ("courses:resource_update", [self.resource.pk]),
            ("courses:resource_delete", [self.resource.pk]),
            ("courses:quiz_create", [self.chapter.pk]),
            ("courses:quiz_manage", [self.quiz.pk]),
            ("courses:quiz_update", [self.quiz.pk]),
            ("courses:quiz_delete", [self.quiz.pk]),
            ("courses:question_create", [self.quiz.pk]),
            ("courses:question_update", [self.question.pk]),
            ("courses:question_delete", [self.question.pk]),
        ):
            self.check(reverse(name, args=args), not_found)
        for name in ("courses:quiz_publish", "courses:quiz_unpublish", "courses:quiz_generate"):
            self.check(reverse(name, args=[self.quiz.pk]), not_found, method="post")
