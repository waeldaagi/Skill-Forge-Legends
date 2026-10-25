import tempfile
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
        # Dossier temporaire : le test ne touche jamais au rapport versionné dans docs/ia/.
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "quiz_generation.md"

            call_command(
                "evaluate_quiz_generation",
                "--provider",
                "mock",
                "--output",
                str(report_path),
                stdout=StringIO(),
            )

            self.assertIn("Sorties JSON valides : 5/5", report_path.read_text(encoding="utf-8"))
