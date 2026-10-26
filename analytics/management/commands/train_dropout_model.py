import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analytics.ml import train_and_evaluate


class Command(BaseCommand):
    help = "Compare les modèles de risque d'abandon et sauvegarde le meilleur."

    def add_arguments(self, parser):
        parser.add_argument("--dataset", default="analytics/fixtures/dropout_dataset.json")
        parser.add_argument("--model", default="analytics/artifacts/dropout_model.joblib")
        parser.add_argument("--metrics", default="analytics/artifacts/dropout_metrics.json")
        parser.add_argument("--docs", default="docs/ia/dropout.md")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        dataset = Path(options["dataset"])
        if not dataset.exists():
            raise CommandError(f"Jeu de données introuvable : {dataset}")
        rows = json.loads(dataset.read_text(encoding="utf-8"))
        result = train_and_evaluate(
            rows, options["model"], options["metrics"], options["seed"]
        )
        best = result["models"][result["best_model"]]
        docs = Path(options["docs"])
        docs.parent.mkdir(parents=True, exist_ok=True)
        docs.write_text(
            "# Prédiction du risque d'abandon\n\n"
            "Ce résultat est basé sur un jeu de données **synthétique** généré "
            "avec des règles réalistes, du bruit et une graine reproductible. "
            "Il ne représente pas des apprenants réels.\n\n"
            "## Variables\n\n"
            "Jours depuis la dernière activité, progression, score moyen aux quiz, "
            "sessions de mentorat, messages du forum et ancienneté du compte.\n\n"
            "## Évaluation\n\n"
            f"Jeu de données : {result['dataset_size']} observations ; "
            f"test : {result['test_size']} observations.\n\n"
            f"Modèle retenu : **{result['best_model']}**.\n\n"
            "| Modèle | Accuracy | Précision | Rappel | F1 | ROC-AUC | Matrice |\n"
            "|---|---:|---:|---:|---:|---:|---|\n"
            + "".join(
                f"| {name} | {values['accuracy']} | {values['precision']} | "
                f"{values['recall']} | {values['f1']} | {values['roc_auc']} | "
                f"`{values['confusion_matrix']}` |\n"
                for name, values in result["models"].items()
            )
            + "\nLes seuils d'affichage sont : faible (< 0,34), moyen (0,34 à 0,66) "
            "et élevé (≥ 0,67).\n",
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(
            f"Modèle retenu : {result['best_model']} (F1={best['f1']})."
        ))
