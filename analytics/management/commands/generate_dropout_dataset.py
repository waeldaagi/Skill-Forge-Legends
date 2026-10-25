import json
from pathlib import Path

from django.core.management.base import BaseCommand

from analytics.ml import generate_dataset


class Command(BaseCommand):
    help = "Génère un jeu de données synthétique pour le risque d'abandon."

    def add_arguments(self, parser):
        parser.add_argument("--samples", type=int, default=200)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--output",
            default="analytics/fixtures/dropout_dataset.json",
            help="Chemin du fichier JSON de sortie.",
        )

    def handle(self, *args, **options):
        rows = generate_dataset(options["samples"], options["seed"])
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"{len(rows)} observations écrites dans {output}."))

