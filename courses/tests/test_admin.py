from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from courses.models import (
    Category,
    Chapter,
    ChapterProgress,
    Choice,
    Course,
    Enrollment,
    Question,
    Quiz,
    QuizAttempt,
    Resource,
)

from .factories import ChapterFactory, CourseFactory


class CourseAdminTests(TestCase):
    def test_course_models_are_registered_in_admin(self):
        expected_models = {
            Category,
            Chapter,
            ChapterProgress,
            Choice,
            Course,
            Enrollment,
            Question,
            Quiz,
            QuizAttempt,
            Resource,
        }

        self.assertTrue(expected_models.issubset(admin.site._registry))

    def test_admin_can_view_course_changelist(self):
        admin_user = User.objects.create_superuser(
            "administrateur", "admin@skillforge.test", "mot-de-passe"
        )
        CourseFactory()
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:courses_course_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cours")

    def test_admin_can_search_quizzes(self):
        admin_user = User.objects.create_superuser(
            "administrateur", "admin@skillforge.test", "mot-de-passe"
        )
        chapter = ChapterFactory()
        Quiz.objects.create(chapter=chapter, title="Quiz Django")
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:courses_quiz_changelist"), {"q": "Quiz Django"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quiz Django")

    def test_non_staff_user_cannot_open_admin(self):
        self.client.force_login(UserFactory(role=User.Role.FORMATEUR))

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_admin_add_and_change_pages_open(self):
        # Un slug prérempli sur un champ non éditable faisait planter ces pages.
        admin_user = User.objects.create_superuser(
            "administrateur", "admin@skillforge.test", "mot-de-passe"
        )
        course = CourseFactory()
        self.client.force_login(admin_user)

        for url in (
            reverse("admin:courses_course_add"),
            reverse("admin:courses_course_change", args=[course.pk]),
            reverse("admin:courses_category_add"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
