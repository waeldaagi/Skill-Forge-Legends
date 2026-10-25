from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.tests.factories import UserFactory
from courses.models import ChapterProgress, Enrollment, Resource
from courses.services import (
    course_progress,
    enroll_learner,
    is_course_completed,
    mark_chapter_completed,
    user_can_access_course,
)

from .factories import ChapterFactory, CourseFactory


class CourseServiceTests(TestCase):
    def test_premium_course_requires_an_authenticated_user(self):
        course = CourseFactory(is_premium=True)

        self.assertFalse(user_can_access_course(None, course))

    def test_enrolling_twice_keeps_one_enrollment(self):
        learner = UserFactory()
        course = CourseFactory()

        enroll_learner(learner, course)
        enroll_learner(learner, course)

        self.assertEqual(Enrollment.objects.filter(learner=learner, course=course).count(), 1)

    def test_marking_chapters_completed_returns_full_progress(self):
        learner = UserFactory()
        first = ChapterFactory(order=1)
        second = ChapterFactory(course=first.course, order=2)

        mark_chapter_completed(learner, first)
        mark_chapter_completed(learner, second)

        self.assertEqual(course_progress(learner, first.course), 100)
        self.assertTrue(is_course_completed(learner, first.course))
        self.assertEqual(ChapterProgress.objects.filter(enrollment__learner=learner).count(), 2)


class ResourceValidationTests(TestCase):
    def test_resource_rejects_both_file_and_link(self):
        resource = Resource(chapter=ChapterFactory(), title="Support", url="https://example.test")
        resource.file.name = "support.pdf"

        with self.assertRaisesMessage(
            ValidationError, "Une ressource doit contenir un fichier ou un lien"
        ):
            resource.full_clean()
