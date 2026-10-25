import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

import httpx
from django.core.management import call_command
from django.test import TestCase

from core.ai.providers.mock import MockProvider


def rejected_key():
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models")
    response = httpx.Response(401, request=request)
    return httpx.HTTPStatusError("HTTP 401", request=request, response=response)


class EvaluateModerationCommandTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command(
            "evaluate_moderation", "--provider", "mock", *args, stdout=out, stderr=StringIO()
        )
        return out.getvalue()

    def test_report_gives_metrics_confusion_matrix_baseline_and_latency(self):
        report = self.run_command("--limit", "8")

        for section in ("Métriques par classe", "Matrice de confusion", "baseline", "Latence"):
            with self.subTest(section=section):
                self.assertIn(section, report)

    def test_mock_provider_scores_exactly_like_the_keyword_baseline(self):
        report = self.run_command()

        ia, baseline = (
            line.split("|")[2:]
            for line in report.splitlines()
            if line.startswith(("| IA |", "| Mots-clés |"))
        )
        self.assertEqual(ia, baseline)

    def test_results_are_written_to_a_markdown_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "resultats.md"

            self.run_command("--limit", "4", "--output", str(path))

            self.assertTrue(path.read_text(encoding="utf-8").startswith("## Résultats du"))

    def test_failed_calls_are_reported_not_hidden(self):
        with (
            mock.patch.object(MockProvider, "generate", side_effect=rejected_key()),
            self.assertLogs("core.ai.client", "WARNING"),
        ):
            report = self.run_command("--limit", "3")

        self.assertIn("3 échec(s) d'appel", report)
        self.assertIn("Aucun appel réussi", report)
