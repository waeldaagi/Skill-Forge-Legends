from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from courses.models import Choice, Question, Quiz, Resource

from .factories import ChapterFactory, CourseFactory


class CourseCatalogueTests(TestCase):
    def test_trainer_can_create_question_with_four_choices(self):
        trainer = UserFactory(role=User.Role.FORMATEUR)
        course = CourseFactory(trainer=trainer)
        chapter = ChapterFactory(course=course)
        quiz = Quiz.objects.create(chapter=chapter, title="Quiz Django")
        self.client.force_login(trainer)

        response = self.client.post(
            reverse("courses:question_create", kwargs={"quiz_pk": quiz.pk}),
            {
                "statement": "Quel objet décrit les données ?",
                "explanation": "Le modèle décrit les données.",
                "evidence": "Le chapitre présente les modèles.",
                "order": 1,
                "choice_1": "Un modèle",
                "choice_2": "Une URL",
                "choice_3": "Un gabarit",
                "choice_4": "Une vue",
                "correct_choice": 1,
            },
        )

        self.assertRedirects(response, reverse("courses:quiz_manage", kwargs={"pk": quiz.pk}))
        self.assertEqual(quiz.questions.get().choices.count(), 4)
        self.assertTrue(quiz.questions.get().choices.get(text="Un modèle").is_correct)

    def test_trainer_can_publish_only_a_complete_quiz(self):
        trainer = UserFactory(role=User.Role.FORMATEUR)
        course = CourseFactory(trainer=trainer)
        chapter = ChapterFactory(course=course)
        quiz = Quiz.objects.create(chapter=chapter, title="Quiz Django")
        question = Question.objects.create(
            quiz=quiz,
            statement="Question",
            explanation="Explication",
            evidence="Preuve",
            order=1,
        )
        Choice.objects.bulk_create(
            [
                Choice(question=question, text=f"Choix {index}", is_correct=index == 1)
                for index in range(1, 5)
            ]
        )
        self.client.force_login(trainer)

        response = self.client.post(reverse("courses:quiz_publish", kwargs={"pk": quiz.pk}))

        self.assertRedirects(response, reverse("courses:quiz_manage", kwargs={"pk": quiz.pk}))
        quiz.refresh_from_db()
        self.assertTrue(quiz.is_published)

    def test_trainer_can_generate_a_draft_quiz_with_mock_ai(self):
        trainer = UserFactory(role=User.Role.FORMATEUR)
        course = CourseFactory(trainer=trainer)
        chapter = ChapterFactory(course=course)
        quiz = Quiz.objects.create(chapter=chapter, title="Quiz généré")
        self.client.force_login(trainer)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("courses:quiz_generate", kwargs={"pk": quiz.pk}))

        quiz.refresh_from_db()
        self.assertRedirects(response, reverse("courses:quiz_manage", kwargs={"pk": quiz.pk}))
        self.assertTrue(quiz.is_ai_generated)
        self.assertFalse(quiz.is_published)
        self.assertEqual(quiz.questions.count(), 1)
        self.assertEqual(quiz.questions.first().choices.count(), 4)

    def test_course_image_is_visible_in_catalogue_and_detail(self):
        course = CourseFactory(
            title="Django illustré",
            image=SimpleUploadedFile(
                "django.png",
                (
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                    b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\xf0"
                    b"\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
                ),
                content_type="image/png",
            ),
        )

        catalogue = self.client.get(reverse("courses:list"))
        detail = self.client.get(course.get_absolute_url())

        self.assertContains(catalogue, course.image.url)
        self.assertContains(catalogue, f"Illustration du cours {course.title}")
        self.assertContains(detail, course.image.url)

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
