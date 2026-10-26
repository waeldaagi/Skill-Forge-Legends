import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase


class DropoutCommandTests(SimpleTestCase):
    """Dossier temporaire : les fichiers versionnés (jeu, métriques, rapport) restent intacts."""

    def test_generate_then_train_writes_dataset_model_metrics_and_report(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            dataset = folder / "dataset.json"

            call_command(
                "generate_dropout_dataset",
                "--samples",
                "80",
                "--output",
                str(dataset),
                stdout=StringIO(),
            )
            call_command(
                "train_dropout_model",
                "--dataset",
                str(dataset),
                "--model",
                str(folder / "model.joblib"),
                "--metrics",
                str(folder / "metrics.json"),
                "--docs",
                str(folder / "report.md"),
                stdout=StringIO(),
            )

            self.assertEqual(len(json.loads(dataset.read_text(encoding="utf-8"))), 80)
            self.assertTrue((folder / "model.joblib").exists())
            metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
            self.assertIn(metrics["best_model"], {"logistic_regression", "random_forest"})
            self.assertIn("synthétique", (folder / "report.md").read_text(encoding="utf-8"))

    def test_training_without_dataset_stops_with_a_clear_message(self):
        with self.assertRaisesMessage(Exception, "Jeu de données introuvable"):
            call_command("train_dropout_model", "--dataset", "absent.json", stdout=StringIO())
