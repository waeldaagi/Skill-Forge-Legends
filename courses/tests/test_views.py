from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from courses.models import Resource

from .factories import ChapterFactory, CourseFactory


class CourseCatalogueTests(TestCase):
    def test_learner_can_see_a_resource_added_to_a_chapter(self):
        learner = UserFactory(role=User.Role.APPRENANT)
        course = CourseFactory(status="PUBLISHED")
        chapter = ChapterFactory(course=course)
        resource = Resource.objects.create(
            chapter=chapter,
            title="Support du chapitre",
            file=SimpleUploadedFile("support.pdf", b"contenu PDF", content_type="application/pdf"),
        )
        self.client.force_login(learner)

        response = self.client.get(reverse("courses:chapter", kwargs={"pk": chapter.pk}))

        self.assertTemplateUsed(response, "courses/chapter.html")
        self.assertContains(response, resource.title)
        self.assertContains(response, resource.file.url)

    def test_catalogue_filters_courses_by_search(self):
        matching = CourseFactory(title="Django du modèle au déploiement")
        CourseFactory(title="Docker pour développeurs")

        response = self.client.get(reverse("courses:list"), {"query": "Django"})

        self.assertTemplateUsed(response, "courses/list.html")
        self.assertEqual(list(response.context["courses"]), [matching])

    def test_formateur_can_create_a_course_owned_by_them(self):
        trainer = UserFactory(role=User.Role.FORMATEUR)
        self.client.force_login(trainer)

        response = self.client.post(
            reverse("courses:create"),
            {
                "title": "APIs Django robustes",
                "description": "Construire une API claire.",
                "level": "BEGINNER",
                "category": matching_category().pk,
                "status": "DRAFT",
            },
        )

        self.assertRedirects(
            response, reverse("courses:update", kwargs={"slug": "apis-django-robustes"})
        )
        self.assertEqual(trainer.courses.get().title, "APIs Django robustes")

    def test_learner_cannot_create_a_course(self):
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))

        response = self.client.get(reverse("courses:create"))

        self.assertEqual(response.status_code, 403)


def matching_category():
    from .factories import CategoryFactory

    return CategoryFactory(name="Développement web")
