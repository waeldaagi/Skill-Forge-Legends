from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from courses.models import (
    Category,
    Chapter,
    Choice,
    Course,
    Question,
    Quiz,
    QuizAttempt,
    Resource,
)
from courses.services import UNVERIFIED_TRAINER_MESSAGE, mark_chapter_completed

from .factories import (
    ChapterFactory,
    CourseFactory,
    QuizFactory,
    TrainerFactory,
    complete_question,
)


def question_data(**overrides):
    data = {
        "statement": "Quel objet décrit les données ?",
        "explanation": "Le modèle décrit les données.",
        "evidence": "Le chapitre présente les modèles.",
        "order": 1,
        "choice_1": "Un modèle",
        "choice_2": "Une URL",
        "choice_3": "Un gabarit",
        "choice_4": "Une vue",
        "correct_choice": 1,
    }
    data.update(overrides)
    return data


def course_data(**overrides):
    data = {
        "title": "APIs Django robustes",
        "description": "Construire une API claire.",
        "level": "BEGINNER",
        # Catégorie créée par la migration 0005 (catégories par défaut).
        "category": Category.objects.get(name="Développement web").pk,
        "status": "DRAFT",
    }
    data.update(overrides)
    return data


class CourseCatalogueTests(TestCase):
    def test_trainer_can_create_question_with_four_choices(self):
        trainer = TrainerFactory()
        quiz = QuizFactory(chapter__course__trainer=trainer, is_published=False)
        self.client.force_login(trainer)

        response = self.client.post(
            reverse("courses:question_create", kwargs={"quiz_pk": quiz.pk}), question_data()
        )

        self.assertRedirects(response, reverse("courses:quiz_manage", kwargs={"pk": quiz.pk}))
        self.assertEqual(quiz.questions.get().choices.count(), 4)
        self.assertTrue(quiz.questions.get().choices.get(text="Un modèle").is_correct)

    def test_question_form_displays_an_explicit_save_button(self):
        trainer = TrainerFactory()
        quiz = QuizFactory(chapter__course__trainer=trainer, is_published=False)
        self.client.force_login(trainer)

        response = self.client.get(reverse("courses:question_create", kwargs={"quiz_pk": quiz.pk}))

        self.assertTemplateUsed(response, "courses/question_form.html")
        self.assertContains(response, "Contenu de la question")
        self.assertContains(response, "Réponses proposées")
        self.assertContains(response, "Enregistrer la question")
        self.assertContains(response, 'name="choice_1"')

    def test_trainer_can_publish_only_a_complete_quiz(self):
        trainer = TrainerFactory()
        quiz = QuizFactory(chapter__course__trainer=trainer, is_published=False)
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

    def test_trainer_sees_the_publish_link_for_a_draft_quiz(self):
        trainer = TrainerFactory()
        quiz = QuizFactory(chapter__course__trainer=trainer, is_published=False)
        self.client.force_login(trainer)

        response = self.client.get(quiz.chapter.course.get_absolute_url())

        self.assertContains(response, reverse("courses:quiz_manage", kwargs={"pk": quiz.pk}))
        self.assertContains(response, "Publier le quiz")

    def test_trainer_can_generate_a_draft_quiz_with_mock_ai(self):
        trainer = TrainerFactory()
        quiz = QuizFactory(chapter__course__trainer=trainer, is_published=False)
        self.client.force_login(trainer)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("courses:quiz_generate", kwargs={"pk": quiz.pk}))

        quiz.refresh_from_db()
        self.assertRedirects(response, reverse("courses:quiz_manage", kwargs={"pk": quiz.pk}))
        self.assertTrue(quiz.is_ai_generated)
        self.assertFalse(quiz.is_published)
        self.assertEqual(quiz.questions.count(), 3)
        self.assertEqual(
            quiz.questions.values_list("statement", flat=True).distinct().count(),
            3,
        )
        self.assertTrue(all(question.choices.count() == 4 for question in quiz.questions.all()))

    @patch("courses.ai.quiz_generation.PdfReader")
    def test_quiz_generation_source_includes_attached_pdf_text(self, pdf_reader):
        from courses.ai.quiz_generation import build_chapter_source

        chapter = ChapterFactory(content="Introduction du chapitre")
        Resource.objects.create(
            chapter=chapter,
            title="Support PDF",
            file=SimpleUploadedFile("support.pdf", b"pdf", content_type="application/pdf"),
        )
        page = MagicMock()
        page.extract_text.return_value = "Les vues Django traitent les requêtes."
        pdf_reader.return_value.pages = [page]

        source = build_chapter_source(chapter)

        self.assertIn("Introduction du chapitre", source)
        self.assertIn("Support PDF", source)
        self.assertIn("Les vues Django traitent les requêtes.", source)

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

        response = self.client.post(reverse("courses:create"), course_data())

        self.assertRedirects(
            response, reverse("courses:update", kwargs={"slug": "apis-django-robustes"})
        )
        self.assertEqual(trainer.courses.get().title, "APIs Django robustes")

    def test_learner_cannot_create_a_course(self):
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))

        response = self.client.get(reverse("courses:create"))

        self.assertEqual(response.status_code, 403)


class CourseUrlTests(TestCase):
    def test_a_course_titled_nouveau_opens_its_own_page(self):
        course = CourseFactory(title="Nouveau")

        response = self.client.get("/cours/nouveau/")

        self.assertEqual(course.slug, "nouveau")
        self.assertEqual(response.context["course"], course)

    def test_anonymous_visitor_is_sent_to_login_from_trainer_pages(self):
        chapter = ChapterFactory()
        quiz = QuizFactory(chapter=chapter)

        for url in (
            reverse("courses:quiz_create", args=[chapter.pk]),
            reverse("courses:question_create", args=[quiz.pk]),
            reverse("courses:chapter_create", args=[chapter.course.pk]),
            reverse("courses:resource_create", args=[chapter.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")


class PremiumQuizTests(TestCase):
    def setUp(self):
        self.course = CourseFactory(is_premium=True)
        self.quiz = QuizFactory(chapter__course=self.course)
        complete_question(self.quiz)
        self.learner = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(self.learner)

    @patch("courses.services.has_active_subscription", return_value=False)
    def test_premium_quiz_is_hidden_without_subscription(self, _subscription):
        url = reverse("courses:quiz", args=[self.quiz.pk])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {}).status_code, 404)
        self.assertFalse(QuizAttempt.objects.exists())

    @patch("courses.services.has_active_subscription", return_value=True)
    def test_premium_quiz_opens_with_a_subscription(self, _subscription):
        response = self.client.get(reverse("courses:quiz", args=[self.quiz.pk]))

        self.assertEqual(response.status_code, 200)

    @patch("courses.services.has_active_subscription", return_value=False)
    def test_trainer_previews_the_quiz_of_their_own_premium_course(self, _subscription):
        self.client.force_login(self.course.trainer)

        response = self.client.get(reverse("courses:quiz", args=[self.quiz.pk]))

        self.assertContains(response, "seuls les apprenants peuvent y répondre")
        self.assertNotContains(response, "Terminer le quiz")


class QuizSubmissionTests(TestCase):
    def setUp(self):
        self.quiz = QuizFactory()
        self.first = complete_question(self.quiz, order=1, correct=1)
        self.second = complete_question(self.quiz, order=2, correct=2)
        self.learner = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(self.learner)
        self.url = reverse("courses:quiz", args=[self.quiz.pk])

    def answer(self, question, number):
        return str(question.choices.order_by("id")[number - 1].pk)

    def test_correct_answers_give_a_full_score(self):
        response = self.client.post(
            self.url,
            {
                f"question-{self.first.pk}": self.answer(self.first, 1),
                f"question-{self.second.pk}": self.answer(self.second, 2),
            },
        )

        self.assertRedirects(response, self.url)
        attempt = QuizAttempt.objects.get()
        self.assertEqual(attempt.score, 100)
        self.assertEqual(
            attempt.answers,
            {
                str(self.first.pk): int(self.answer(self.first, 1)),
                str(self.second.pk): int(self.answer(self.second, 2)),
            },
        )

    def test_a_forged_answer_counts_as_wrong_without_error(self):
        response = self.client.post(
            self.url,
            {
                f"question-{self.first.pk}": "abc",
                # Bonne réponse de l'autre question : elle ne compte pas pour celle-ci.
                f"question-{self.second.pk}": self.answer(self.first, 1),
            },
        )

        self.assertRedirects(response, self.url)
        attempt = QuizAttempt.objects.get()
        self.assertEqual(attempt.score, 0)
        self.assertEqual(attempt.answers, {str(self.first.pk): None, str(self.second.pk): None})

    def test_a_quiz_without_question_records_no_attempt(self):
        empty = QuizFactory(chapter=self.quiz.chapter)

        response = self.client.post(reverse("courses:quiz", args=[empty.pk]))

        self.assertRedirects(response, reverse("courses:quiz", args=[empty.pk]))
        self.assertFalse(QuizAttempt.objects.exists())

    def test_draft_quiz_is_not_found(self):
        draft = QuizFactory(chapter=self.quiz.chapter, is_published=False)

        self.assertEqual(self.client.get(reverse("courses:quiz", args=[draft.pk])).status_code, 404)


class LearnerProgressTests(TestCase):
    def test_course_page_shows_the_progress_of_an_enrolled_learner(self):
        first = ChapterFactory(order=1)
        ChapterFactory(course=first.course, order=2)
        learner = UserFactory(role=User.Role.APPRENANT)
        mark_chapter_completed(learner, first)
        self.client.force_login(learner)

        response = self.client.get(first.course.get_absolute_url())

        self.assertContains(response, "Progression : 50 %")
        self.assertContains(response, 'value="50" max="100"')
        self.assertContains(response, "Terminé")
        self.assertNotContains(response, "S’inscrire à ce cours")

    def test_completing_a_chapter_enrolls_the_learner(self):
        chapter = ChapterFactory()
        learner = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(learner)

        response = self.client.post(reverse("courses:complete_chapter", args=[chapter.pk]))

        self.assertRedirects(response, chapter.course.get_absolute_url())
        self.assertTrue(learner.enrollments.filter(course=chapter.course).exists())

    def test_trainer_does_not_see_the_complete_button(self):
        chapter = ChapterFactory()
        self.client.force_login(chapter.course.trainer)

        response = self.client.get(reverse("courses:chapter", args=[chapter.pk]))

        self.assertNotContains(response, "Marquer ce chapitre comme terminé")


class ChapterVideoTests(TestCase):
    def test_youtube_watch_link_is_embedded(self):
        chapter = ChapterFactory(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.client.force_login(UserFactory())

        response = self.client.get(reverse("courses:chapter", args=[chapter.pk]))

        self.assertContains(response, 'src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"')
        self.assertContains(response, f'title="Vidéo du chapitre {chapter.title}"')
        # Sans référent, YouTube refuse la lecture (erreur 153) : Django envoie « same-origin ».
        self.assertContains(response, 'referrerpolicy="strict-origin-when-cross-origin"')

    def test_other_video_sites_get_a_link_instead_of_an_iframe(self):
        chapter = ChapterFactory(video_url="https://example.com/video.mp4")
        self.client.force_login(UserFactory())

        response = self.client.get(reverse("courses:chapter", args=[chapter.pk]))

        self.assertNotContains(response, "<iframe")
        self.assertContains(response, 'href="https://example.com/video.mp4"')


class UnverifiedTrainerTests(TestCase):
    def setUp(self):
        self.trainer = UserFactory(role=User.Role.FORMATEUR, is_verified=False)
        self.client.force_login(self.trainer)

    def test_unverified_trainer_cannot_publish_a_course(self):
        response = self.client.post(reverse("courses:create"), course_data(status="PUBLISHED"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, UNVERIFIED_TRAINER_MESSAGE)
        self.assertFalse(Course.objects.exists())

    def test_unverified_trainer_cannot_publish_an_existing_draft(self):
        course = CourseFactory(trainer=self.trainer, status=Course.Status.DRAFT)

        response = self.client.post(
            reverse("courses:update", args=[course.slug]),
            course_data(title=course.title, status="PUBLISHED"),
        )

        self.assertContains(response, UNVERIFIED_TRAINER_MESSAGE)
        course.refresh_from_db()
        self.assertEqual(course.status, Course.Status.DRAFT)

    def test_unverified_trainer_cannot_publish_a_quiz(self):
        quiz = QuizFactory(chapter__course__trainer=self.trainer, is_published=False)
        complete_question(quiz)

        response = self.client.post(reverse("courses:quiz_publish", args=[quiz.pk]), follow=True)

        self.assertContains(response, UNVERIFIED_TRAINER_MESSAGE)
        quiz.refresh_from_db()
        self.assertFalse(quiz.is_published)

    def test_my_courses_page_warns_an_unverified_trainer(self):
        response = self.client.get(reverse("courses:trainer_courses"))

        self.assertContains(response, "pas encore vérifié")


class TrainerCourseTests(TestCase):
    def setUp(self):
        self.trainer = TrainerFactory()
        self.client.force_login(self.trainer)

    def test_my_courses_lists_only_my_courses_with_their_drafts(self):
        mine = CourseFactory(trainer=self.trainer, status=Course.Status.DRAFT)
        CourseFactory()

        response = self.client.get(reverse("courses:trainer_courses"))

        self.assertEqual(list(response.context["courses"]), [mine])
        self.assertContains(response, "Brouillon")

    def test_trainer_opens_their_own_draft_course_and_its_chapters(self):
        chapter = ChapterFactory(course__trainer=self.trainer, course__status=Course.Status.DRAFT)

        course_page = self.client.get(chapter.course.get_absolute_url())
        chapter_page = self.client.get(reverse("courses:chapter", args=[chapter.pk]))

        self.assertContains(course_page, "ce cours n'est visible que par vous")
        self.assertEqual(chapter_page.status_code, 200)

    def test_draft_course_stays_hidden_from_others(self):
        chapter = ChapterFactory(course__status=Course.Status.DRAFT)
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))

        self.assertEqual(self.client.get(chapter.course.get_absolute_url()).status_code, 404)
        self.assertEqual(
            self.client.get(reverse("courses:chapter", args=[chapter.pk])).status_code, 404
        )

    def test_renaming_a_course_keeps_its_address(self):
        course = CourseFactory(trainer=self.trainer, title="Django avancé")

        self.client.post(
            reverse("courses:update", args=[course.slug]),
            course_data(title="Django avancé : édition 2026", status="PUBLISHED"),
        )

        course.refresh_from_db()
        self.assertEqual(course.title, "Django avancé : édition 2026")
        self.assertEqual(course.slug, "django-avance")

    def test_two_courses_with_the_same_title_get_distinct_addresses(self):
        CourseFactory(title="APIs Django robustes")

        response = self.client.post(reverse("courses:create"), course_data())

        self.assertRedirects(
            response, reverse("courses:update", kwargs={"slug": "apis-django-robustes-2"})
        )

    def test_deleting_a_course_returns_to_my_courses(self):
        course = CourseFactory(trainer=self.trainer)

        response = self.client.post(reverse("courses:delete", args=[course.slug]))

        self.assertRedirects(response, reverse("courses:trainer_courses"))
        self.assertFalse(Course.objects.exists())


class TrainerChapterAndResourceTests(TestCase):
    def setUp(self):
        self.trainer = TrainerFactory()
        self.course = CourseFactory(trainer=self.trainer)
        self.chapter = ChapterFactory(course=self.course, order=1)
        self.client.force_login(self.trainer)

    def chapter_data(self, **overrides):
        data = {"title": "Les vues", "order": 2, "content": "Une vue reçoit une requête."}
        data.update(overrides)
        return data

    def test_new_chapter_form_suggests_the_next_position(self):
        response = self.client.get(reverse("courses:chapter_create", args=[self.course.pk]))

        self.assertEqual(response.context["form"].initial["order"], 2)

    def test_a_taken_chapter_position_is_refused_without_error(self):
        response = self.client.post(
            reverse("courses:chapter_create", args=[self.course.pk]), self.chapter_data(order=1)
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "occupe déjà cette position")
        self.assertEqual(self.course.chapters.count(), 1)

    def test_video_link_without_protocol_is_saved_in_https(self):
        self.client.post(
            reverse("courses:chapter_create", args=[self.course.pk]),
            self.chapter_data(video_url="youtu.be/dQw4w9WgXcQ"),
        )

        self.assertEqual(
            self.course.chapters.get(order=2).video_url, "https://youtu.be/dQw4w9WgXcQ"
        )

    def test_trainer_updates_then_deletes_a_chapter(self):
        url = reverse("courses:chapter_update", args=[self.chapter.pk])

        response = self.client.post(url, self.chapter_data(title="Modèles revus", order=1))

        self.assertRedirects(response, self.course.get_absolute_url())
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.title, "Modèles revus")

        response = self.client.post(reverse("courses:chapter_delete", args=[self.chapter.pk]))

        self.assertRedirects(response, self.course.get_absolute_url())
        self.assertFalse(Chapter.objects.exists())

    def test_trainer_adds_updates_and_deletes_a_resource(self):
        response = self.client.post(
            reverse("courses:resource_create", args=[self.chapter.pk]),
            {"title": "Documentation", "url": "https://docs.djangoproject.com/"},
        )
        chapter_url = reverse("courses:chapter", args=[self.chapter.pk])
        self.assertRedirects(response, chapter_url)
        resource = self.chapter.resources.get()

        response = self.client.post(
            reverse("courses:resource_update", args=[resource.pk]),
            {"title": "Documentation officielle", "url": "https://docs.djangoproject.com/fr/"},
        )
        self.assertRedirects(response, chapter_url)
        resource.refresh_from_db()
        self.assertEqual(resource.title, "Documentation officielle")

        response = self.client.post(reverse("courses:resource_delete", args=[resource.pk]))
        self.assertRedirects(response, chapter_url)
        self.assertFalse(Resource.objects.exists())

    def test_resource_over_five_megabytes_is_refused(self):
        big_file = SimpleUploadedFile(
            "support.pdf", b"0" * (5 * 1024 * 1024 + 1), content_type="application/pdf"
        )

        response = self.client.post(
            reverse("courses:resource_create", args=[self.chapter.pk]),
            {"title": "Support trop lourd", "file": big_file},
        )

        self.assertContains(response, "taille maximale de 5 Mo")
        self.assertFalse(Resource.objects.exists())


class TrainerQuizTests(TestCase):
    def setUp(self):
        self.trainer = TrainerFactory()
        self.quiz = QuizFactory(chapter__course__trainer=self.trainer, is_published=False)
        self.question = complete_question(self.quiz)
        self.client.force_login(self.trainer)

    def test_identical_choices_are_refused_without_error(self):
        response = self.client.post(
            reverse("courses:question_create", args=[self.quiz.pk]),
            question_data(order=2, choice_2="un modèle"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "identique à un autre choix")
        self.assertEqual(self.quiz.questions.count(), 1)

    def test_a_taken_question_position_is_refused_without_error(self):
        response = self.client.post(
            reverse("courses:question_create", args=[self.quiz.pk]), question_data(order=1)
        )

        self.assertContains(response, "occupe déjà cette position")
        self.assertEqual(self.quiz.questions.count(), 1)

    def test_editing_a_question_keeps_its_own_position(self):
        response = self.client.post(
            reverse("courses:question_update", args=[self.question.pk]),
            question_data(order=1, statement="Énoncé corrigé"),
        )

        self.assertRedirects(response, reverse("courses:quiz_manage", args=[self.quiz.pk]))
        self.question.refresh_from_db()
        self.assertEqual(self.question.statement, "Énoncé corrigé")

    def test_trainer_deletes_a_question_then_the_quiz(self):
        manage_url = reverse("courses:quiz_manage", args=[self.quiz.pk])

        response = self.client.post(reverse("courses:question_delete", args=[self.question.pk]))
        self.assertRedirects(response, manage_url)
        self.assertFalse(Question.objects.exists())

        response = self.client.post(reverse("courses:quiz_delete", args=[self.quiz.pk]))
        self.assertRedirects(response, self.quiz.chapter.course.get_absolute_url())
        self.assertFalse(Quiz.objects.exists())

    def test_trainer_unpublishes_a_quiz(self):
        self.quiz.is_published = True
        self.quiz.save()

        response = self.client.post(reverse("courses:quiz_unpublish", args=[self.quiz.pk]))

        self.assertRedirects(response, reverse("courses:quiz_manage", args=[self.quiz.pk]))
        self.quiz.refresh_from_db()
        self.assertFalse(self.quiz.is_published)

    def test_a_published_quiz_is_not_regenerated(self):
        self.quiz.is_published = True
        self.quiz.save()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("courses:quiz_generate", args=[self.quiz.pk]), follow=True
            )

        self.assertContains(response, "Dépubliez le quiz")
        self.assertEqual(list(self.quiz.questions.all()), [self.question])


class OwnerPagesTests(TestCase):
    def test_trainer_opens_every_page_of_their_own_course(self):
        trainer = TrainerFactory()
        quiz = QuizFactory(chapter__course__trainer=trainer, is_published=False)
        chapter = quiz.chapter
        course = chapter.course
        question = complete_question(quiz)
        resource = Resource.objects.create(
            chapter=chapter, title="Documentation", url="https://docs.djangoproject.com/"
        )
        self.client.force_login(trainer)

        for name, args in (
            ("courses:trainer_courses", []),
            ("courses:create", []),
            ("courses:detail", [course.slug]),
            ("courses:update", [course.slug]),
            ("courses:delete", [course.slug]),
            ("courses:chapter", [chapter.pk]),
            ("courses:chapter_create", [course.pk]),
            ("courses:chapter_update", [chapter.pk]),
            ("courses:chapter_delete", [chapter.pk]),
            ("courses:resource_create", [chapter.pk]),
            ("courses:resource_update", [resource.pk]),
            ("courses:resource_delete", [resource.pk]),
            ("courses:quiz_create", [chapter.pk]),
            ("courses:quiz_manage", [quiz.pk]),
            ("courses:quiz_update", [quiz.pk]),
            ("courses:quiz_delete", [quiz.pk]),
            ("courses:question_create", [quiz.pk]),
            ("courses:question_update", [question.pk]),
            ("courses:question_delete", [question.pk]),
        ):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)


class EnrollmentTests(TestCase):
    def setUp(self):
        self.learner = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(self.learner)

    def test_learner_enrolls_in_a_free_course(self):
        course = CourseFactory()

        response = self.client.post(reverse("courses:enroll", args=[course.slug]))

        self.assertRedirects(response, course.get_absolute_url())
        self.assertTrue(self.learner.enrollments.filter(course=course).exists())

    @patch("courses.services.has_active_subscription", return_value=False)
    def test_premium_course_needs_a_subscription_to_enroll(self, _subscription):
        course = CourseFactory(is_premium=True)

        response = self.client.post(reverse("courses:enroll", args=[course.slug]), follow=True)

        self.assertContains(response, "nécessite un abonnement actif")
        self.assertFalse(self.learner.enrollments.exists())

    @patch("courses.services.has_active_subscription", return_value=False)
    def test_premium_chapter_cannot_be_completed_without_subscription(self, _subscription):
        chapter = ChapterFactory(course__is_premium=True)

        response = self.client.post(reverse("courses:complete_chapter", args=[chapter.pk]))

        self.assertEqual(response.status_code, 404)

    def test_catalogue_filters_by_category_and_level(self):
        wanted = CourseFactory(level=Course.Level.ADVANCED)
        CourseFactory(category=wanted.category, level=Course.Level.BEGINNER)
        CourseFactory(level=Course.Level.ADVANCED)

        response = self.client.get(
            reverse("courses:list"),
            {"category": wanted.category.pk, "level": Course.Level.ADVANCED},
        )

        self.assertEqual(list(response.context["courses"]), [wanted])


class QuizPublicationRulesTests(TestCase):
    def setUp(self):
        self.trainer = TrainerFactory()
        self.quiz = QuizFactory(chapter__course__trainer=self.trainer, is_published=False)
        self.client.force_login(self.trainer)
        self.url = reverse("courses:quiz_publish", args=[self.quiz.pk])

    def test_an_empty_quiz_is_not_published(self):
        response = self.client.post(self.url, follow=True)

        self.assertContains(response, "Ajoutez quatre choix à chaque question")
        self.quiz.refresh_from_db()
        self.assertFalse(self.quiz.is_published)

    def test_a_question_without_a_single_correct_answer_blocks_publication(self):
        question = complete_question(self.quiz)
        question.choices.update(is_correct=False)

        response = self.client.post(self.url, follow=True)

        self.assertContains(response, "une seule bonne réponse")
        self.quiz.refresh_from_db()
        self.assertFalse(self.quiz.is_published)


class ChapterNavigationTests(TestCase):
    def test_chapter_links_to_its_neighbours(self):
        first = ChapterFactory(order=1)
        second = ChapterFactory(course=first.course, order=2)
        third = ChapterFactory(course=first.course, order=3)
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))

        response = self.client.get(reverse("courses:chapter", args=[second.pk]))

        self.assertEqual(response.context["previous_chapter"], first)
        self.assertEqual(response.context["next_chapter"], third)
        self.assertContains(response, "Chapitre suivant")
