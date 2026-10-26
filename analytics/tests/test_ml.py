import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from analytics.ml import FEATURE_NAMES, generate_dataset, predict_dropout_risk, train_and_evaluate


class DropoutModelTests(SimpleTestCase):
    def test_dataset_contains_expected_features_and_both_labels(self):
        rows = generate_dataset(samples=80, seed=7)
        self.assertEqual(len(rows), 80)
        self.assertTrue({row["dropout"] for row in rows} == {0, 1})
        self.assertTrue(set(FEATURE_NAMES).issubset(rows[0]))

    def test_training_saves_model_and_predicts_risk(self):
        rows = generate_dataset(samples=100)
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "dropout.joblib"
            metrics_path = Path(directory) / "metrics.json"
            result = train_and_evaluate(rows, model_path, metrics_path)
            self.assertIn(result["best_model"], {"logistic_regression", "random_forest"})
            self.assertTrue(model_path.exists())
            self.assertTrue(metrics_path.exists())
            prediction = predict_dropout_risk(model_path, rows[0])
            self.assertIn(prediction["level"], {"low", "medium", "high"})
            self.assertGreaterEqual(prediction["probability"], 0)
            self.assertLessEqual(prediction["probability"], 1)
