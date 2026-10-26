import json
import time
from pathlib import Path

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from sklearn.metrics import classification_report, confusion_matrix, mean_absolute_error

from assessment.ai.evaluation import FEATURE
from assessment.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_prompt
from assessment.ai.schemas import AssessmentOutput
from core.ai import AIServiceError, complete_json
from core.ai.providers import get_provider

DATASET = Path(__file__).resolve().parents[2] / "fixtures" / "assessment_dataset.json"


class Command(BaseCommand):
    help = (
        "Évalue la qualité de la décision RÉUSSI/ECHOUÉ, l'écart de score et la latence "
        "sur le jeu de soumissions de référence."
    )

    def add_arguments(self, parser):
        parser.add_argument("--provider", help="mock, gemini… (par défaut : AI_PROVIDER)")
        parser.add_argument("--limit", type=int, help="N'évaluer que les N premières soumissions")
        parser.add_argument("--output", help="Fichier Markdown où écrire les résultats")

    def handle(self, *args, **options):
        provider_name = options["provider"] or settings.AI_PROVIDER
        examples = json.loads(DATASET.read_text(encoding="utf-8"))
        if options["limit"]:
            examples = examples[: options["limit"]]

        rows = []
        for example in examples:
            row = self._evaluate_one(example, provider_name)
            rows.append(row)
            self.stderr.write(
                f"{example['id']}: {example['human_decision']} -> {row['predicted_decision']}"
            )

        report = render_report(rows, provider_name, get_provider(provider_name).model)
        self.stdout.write(report)
        if options["output"]:
            Path(options["output"]).write_text(report, encoding="utf-8")

    def _evaluate_one(self, example, provider_name):
        criteria = example["criteria"]
        prompt = build_prompt(
            certification_title=example["certification_title"],
            instructions=example["instructions"],
            criteria=criteria,
            text_response=example.get("text_response", ""),
            repository_url=example.get("repository_url", ""),
        )

        started = time.perf_counter()
        try:
            output = complete_json(
                FEATURE, SYSTEM_PROMPT, prompt, AssessmentOutput, provider_name=provider_name
            )
        except AIServiceError:
            return {
                "id": example["id"],
                "human_decision": example["human_decision"],
                "human_score": example["human_score"],
                "predicted_decision": "ECHOUEE",
                "predicted_score": 0,
                "latency_ms": None,
            }
        latency_ms = round((time.perf_counter() - started) * 1000)
        predicted_decision = (
            "REUSSIE" if output.total_score >= example["passing_score"] else "ECHOUEE"
        )
        return {
            "id": example["id"],
            "human_decision": example["human_decision"],
            "human_score": example["human_score"],
            "predicted_decision": predicted_decision,
            "predicted_score": output.total_score,
            "latency_ms": latency_ms,
        }


def render_report(rows, provider_name, model_name):
    truth_decisions = [row["human_decision"] for row in rows]
    predicted_decisions = [row["predicted_decision"] for row in rows]
    truth_scores = [row["human_score"] for row in rows]
    predicted_scores = [row["predicted_score"] for row in rows]
    latencies = np.array([row["latency_ms"] for row in rows if row["latency_ms"] is not None])

    report = classification_report(
        truth_decisions,
        predicted_decisions,
        labels=["REUSSIE", "ECHOUEE"],
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(truth_decisions, predicted_decisions, labels=["REUSSIE", "ECHOUEE"])

    now = timezone.localtime().strftime("%d/%m/%Y à %H h %M")
    mae = mean_absolute_error(truth_scores, predicted_scores)
    mean_latency = float(latencies.mean()) if len(latencies) else 0
    p95_latency = float(np.percentile(latencies, 95)) if len(latencies) else 0

    lines = [
        f"## Évaluation du {now}",
        "",
        f"Fournisseur : `{provider_name}` · modèle : `{model_name}` · prompt : `{PROMPT_VERSION}`",
        "",
        "### Décision RÉUSSIE (IA vs humain)",
        "",
        "| Mesure | Valeur |",
        "|---|---|",
        f"| Précision (REUSSIE) | {report['REUSSIE']['precision']:.3f} |",
        f"| Rappel (REUSSIE) | {report['REUSSIE']['recall']:.3f} |",
        f"| F1 (REUSSIE) | {report['REUSSIE']['f1-score']:.3f} |",
        "",
        "### Matrice de confusion",
        "",
        "| Attendu \\ Prédit | REUSSIE | ECHOUEE |",
        "|---|---|---|",
        f"| REUSSIE | {matrix[0][0]} | {matrix[0][1]} |",
        f"| ECHOUEE | {matrix[1][0]} | {matrix[1][1]} |",
        "",
        "### Écart de score",
        "",
        f"Erreur absolue moyenne (IA vs humain) : **{mae:.2f}** points.",
        "",
        "### Latence",
        "",
        f"Latence moyenne : **{mean_latency:.0f} ms** · p95 : **{p95_latency:.0f} ms**.",
        "",
    ]
    return "\n".join(lines)
