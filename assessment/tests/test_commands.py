import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase


class EvaluateAssessmentCommandTests(TestCase):
    """Rapport écrit dans un dossier temporaire : docs/ia/assessment.md reste intact."""

    def test_report_gives_decision_metrics_score_gap_and_latency(self):
        with tempfile.TemporaryDirectory() as folder:
            report_path = Path(folder) / "assessment.md"

            call_command(
                "evaluate_assessment",
                "--provider",
                "mock",
                "--limit",
                "10",
                "--output",
                str(report_path),
                stdout=StringIO(),
                stderr=StringIO(),
            )

            report = report_path.read_text(encoding="utf-8")
        for section in ("Précision", "Matrice de confusion", "Erreur absolue moyenne", "Latence"):
            with self.subTest(section=section):
                self.assertIn(section, report)
