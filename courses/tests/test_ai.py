from unittest.mock import patch

from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase
from pydantic import ValidationError

from core.models import AIJob
from courses.ai import quiz_generation
from courses.ai.quiz_generation import GeneratedQuestion, GeneratedQuiz

from .factories import QuizFactory, TrainerFactory, complete_question


def generated_question(**overrides):
    data = {
        "statement": "Quel fichier déclare les routes ?",
        "choices": ["urls.py", "models.py", "admin.py", "forms.py"],
        "correct_index": 0,
        "explanation": "urls.py associe une route à une vue.",
        "evidence": "Le fichier urls.py déclare les routes.",
    }
    data.update(overrides)
    return data


class GeneratedQuizSchemaTests(SimpleTestCase):
    def test_identical_choices_are_rejected(self):
        with self.assertRaisesMessage(ValidationError, "doivent être différents"):
            GeneratedQuestion(**generated_question(choices=["urls.py", "URLS.py ", "a", "b"]))

    def test_a_choice_longer_than_the_database_field_is_rejected(self):
        with self.assertRaises(ValidationError):
            GeneratedQuestion(**generated_question(choices=["x" * 301, "a", "b", "c"]))

    def test_two_questions_with_the_same_statement_are_rejected(self):
        with self.assertRaisesMessage(ValidationError, "même énoncé"):
            GeneratedQuiz(questions=[generated_question(), generated_question()])

    def test_surrounding_spaces_are_removed(self):
        question = GeneratedQuestion(**generated_question(statement="  Quelle route ?  "))

        self.assertEqual(question.statement, "Quelle route ?")


class QuizGenerationRunTests(TestCase):
    def test_an_error_while_saving_keeps_the_previous_questions(self):
        quiz = QuizFactory(chapter__course__trainer=TrainerFactory(), is_published=False)
        question = complete_question(quiz)
        job = AIJob.objects.create(
            feature="quiz_generation",
            user=quiz.chapter.course.trainer,
            target=quiz,
            payload={"source": "Chapitre : Les routes"},
        )
        output = GeneratedQuiz(questions=[generated_question()])

        with (
            patch.object(quiz_generation, "complete_json", return_value=output),
            patch.object(
                quiz_generation.Choice.objects, "bulk_create", side_effect=IntegrityError("doublon")
            ),
            self.assertRaises(IntegrityError),
        ):
            quiz_generation.run(job)

        self.assertEqual(list(quiz.questions.all()), [question])
        self.assertEqual(question.choices.count(), 4)
