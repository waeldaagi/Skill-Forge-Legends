from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings


class CourseCommandTests(TestCase):
    @override_settings(DEMO_PASSWORD="Demo-Soutenance-2026")
    def test_seed_demo_creates_four_choices(self):
        call_command("seed_demo", stdout=StringIO())

        from courses.models import Quiz

        quiz = Quiz.objects.get(title="Vérifier les bases des modèles")
        self.assertEqual(quiz.questions.get().choices.count(), 4)

    def test_evaluate_command_reports_valid_mock_outputs(self):
        report_path = Path("docs/ia/quiz_generation.md")

        call_command("evaluate_quiz_generation", "--provider", "mock")

        self.assertTrue(report_path.exists())
        self.assertIn("Sorties JSON valides", report_path.read_text(encoding="utf-8"))
        report_path.unlink()
