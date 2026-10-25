import json
import time
from pathlib import Path

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from community.ai.moderation import FEATURE, keyword_label
from community.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_prompt
from community.ai.schemas import ModerationOutput
from core.ai import AIServiceError, complete_json
from core.ai.providers import get_provider

DATASET = Path(__file__).resolve().parents[2] / "fixtures" / "moderation_dataset.json"
LABELS = ["OK", "SPAM", "TOXIQUE", "HORS_SUJET"]
FAILED = "ÉCHEC"
# Quota gratuit (429) ou surcharge (503) : on attend puis on réessaie, trois fois au plus.
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 10


def fr(value, digits=3):
    return f"{value:.{digits}f}".replace(".", ",")


class Command(BaseCommand):
    help = (
        "Évalue la modération automatique sur le jeu étiqueté : précision, rappel et F1 par "
        "classe, matrice de confusion, comparaison avec la baseline par mots-clés, latences."
    )

    def add_arguments(self, parser):
        parser.add_argument("--provider", help="mock, gemini… (par défaut : AI_PROVIDER)")
        parser.add_argument("--limit", type=int, help="N'évaluer que les N premiers messages")
        parser.add_argument("--output", help="Fichier Markdown où écrire les résultats")
        parser.add_argument(
            "--pause", type=float, default=0, help="Secondes d'attente entre deux appels"
        )

    def handle(self, *args, **options):
        provider_name = options["provider"] or settings.AI_PROVIDER
        examples = json.loads(DATASET.read_text(encoding="utf-8"))[: options["limit"]]
        rows = []
        for number, example in enumerate(examples, start=1):
            label, duration_ms = self.classify(example["text"], provider_name)
            rows.append({**example, "predicted": label, "duration_ms": duration_ms})
            self.stderr.write(f"{number}/{len(examples)} {example['label']} -> {label}")
            time.sleep(options["pause"])
        report = render_report(rows, provider_name, get_provider(provider_name).model)
        self.stdout.write(report)
        if options["output"]:
            Path(options["output"]).write_text(report, encoding="utf-8")
            self.stderr.write(self.style.SUCCESS(f"Résultats écrits dans {options['output']}"))

    def classify(self, text, provider_name):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            started = time.perf_counter()
            try:
                output = complete_json(
                    FEATURE,
                    SYSTEM_PROMPT,
                    build_prompt(text),
                    ModerationOutput,
                    provider_name=provider_name,
                )
            except AIServiceError as exc:
                if not exc.retryable or attempt == MAX_ATTEMPTS:
                    return FAILED, None
                time.sleep(RETRY_WAIT_SECONDS * attempt)
            else:
                return output.label, round((time.perf_counter() - started) * 1000)


def render_report(rows, provider_name, model_name):
    answered = [row for row in rows if row["predicted"] != FAILED]
    truth = [row["label"] for row in answered]
    predicted = [row["predicted"] for row in answered]
    baseline = [keyword_label(row["text"]) for row in answered]
    latencies = np.array([row["duration_ms"] for row in answered])
    now = timezone.localtime().strftime("%d/%m/%Y à %H h %M")

    header = [
        f"## Résultats du {now}",
        "",
        f"Fournisseur : `{provider_name}` · modèle : `{model_name}` · prompt : `{PROMPT_VERSION}`"
        f" · {len(rows)} messages, {len(rows) - len(answered)} échec(s) d'appel.",
        "",
    ]
    if not answered:
        return "\n".join([*header, "Aucun appel réussi : aucune métrique à calculer.", ""])
    lines = [
        *header,
        "### Métriques par classe (IA)",
        "",
        *metrics_table(truth, predicted),
        "",
        "### Matrice de confusion (IA)",
        "",
        "Lignes : étiquette attendue. Colonnes : étiquette prédite.",
        "",
        *confusion_table(truth, predicted),
        "",
        "### Comparaison avec la baseline par mots-clés",
        "",
        "| Méthode | Exactitude | F1 macro |",
        "|---|---|---|",
        f"| IA | {fr(accuracy_score(truth, predicted))} | {fr(macro_f1(truth, predicted))} |",
        f"| Mots-clés | {fr(accuracy_score(truth, baseline))} | {fr(macro_f1(truth, baseline))} |",
        "",
        "### Latence par message (appels réussis)",
        "",
        *latency_table(latencies),
        "",
        "### Messages mal classés par l'IA",
        "",
        "| N° | Attendu | Prédit | Message |",
        "|---|---|---|---|",
        *[
            f"| {row['id']} | {row['label']} | {row['predicted']} | {row['text']} |"
            for row in rows
            if row["predicted"] != row["label"]
        ],
        "",
    ]
    return "\n".join(lines)


def latency_table(latencies):
    if latencies.size == 0:
        return ["Aucun appel réussi : pas de latence à mesurer."]
    return [
        "| Moyenne | Médiane | p95 | Maximum |",
        "|---|---|---|---|",
        f"| {latencies.mean():.0f} ms | {np.median(latencies):.0f} ms "
        f"| {np.percentile(latencies, 95):.0f} ms | {latencies.max():.0f} ms |",
    ]


def macro_f1(truth, predicted):
    report = classification_report(
        truth, predicted, labels=LABELS, output_dict=True, zero_division=0
    )
    return report["macro avg"]["f1-score"]


def metrics_table(truth, predicted):
    report = classification_report(
        truth, predicted, labels=LABELS, output_dict=True, zero_division=0
    )
    rows = ["| Classe | Précision | Rappel | F1 | Effectif |", "|---|---|---|---|---|"]
    for name in [*LABELS, "macro avg"]:
        scores = report[name]
        title = "Moyenne macro" if name == "macro avg" else name
        rows.append(
            f"| {title} | {fr(scores['precision'])} | {fr(scores['recall'])} "
            f"| {fr(scores['f1-score'])} | {int(scores['support'])} |"
        )
    rows.append(f"| Exactitude | | | {fr(accuracy_score(truth, predicted))} | {len(truth)} |")
    return rows


def confusion_table(truth, predicted):
    matrix = confusion_matrix(truth, predicted, labels=LABELS)
    rows = [f"| | {' | '.join(LABELS)} |", "|---" * (len(LABELS) + 1) + "|"]
    for label, counts in zip(LABELS, matrix, strict=True):
        rows.append(f"| {label} | {' | '.join(str(count) for count in counts)} |")
    return rows
