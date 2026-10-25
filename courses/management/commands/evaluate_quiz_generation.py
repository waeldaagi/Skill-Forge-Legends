import statistics
import time
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.ai import AIServiceError, complete_json
from courses.ai.quiz_generation import GeneratedQuiz

SAMPLES = (
    "Les modèles Django décrivent les données et leurs règles.",
    "Les URL Django associent une route à une vue.",
    "Les migrations synchronisent les modèles et la base de données.",
    "Les formulaires Django valident et nettoient les données saisies.",
    "Les vues Django traitent les requêtes et renvoient une réponse.",
)


class Command(BaseCommand):
    help = "Mesure la validité et la latence de la génération de quiz."

    def add_arguments(self, parser):
        parser.add_argument("--provider", default="mock", choices=("mock", "gemini"))

    def handle(self, *args, **options):
        provider = options["provider"]
        durations = []
        valid_outputs = 0
        question_count = 0
        failures = []

        for sample in SAMPLES:
            started = time.perf_counter()
            try:
                output = complete_json(
                    "quiz_generation",
                    "Génère des questions QCM pédagogiques.",
                    sample,
                    GeneratedQuiz,
                    provider_name=provider,
                )
            except (AIServiceError, CommandError) as exc:
                failures.append(str(exc))
            else:
                valid_outputs += 1
                question_count += len(output.questions)
            durations.append((time.perf_counter() - started) * 1000)

        report = self._build_report(provider, durations, valid_outputs, question_count, failures)
        report_path = Path("docs/ia/quiz_generation.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Rapport écrit dans {report_path}."))

    @staticmethod
    def _build_report(provider, durations, valid_outputs, question_count, failures):
        count = len(SAMPLES)
        failure_lines = [f"- {failure}" for failure in failures] or ["- Aucun"]
        return "\n".join(
            (
                "# Évaluation de la génération de quiz",
                "",
                "## Cas d'usage",
                "Le formateur utilise la génération pour obtenir un premier brouillon "
                "de QCM à relire avant publication.",
                "",
                "## Jeu de données",
                f"- Taille : {count} extraits synthétiques.",
                "- Source : phrases pédagogiques couvrant les modèles, URL, migrations, "
                "formulaires et vues Django.",
                "- Étiquetage : contrôle automatique du schéma Pydantic, sans étiquette "
                "humaine de pertinence.",
                "",
                "## Résultats",
                f"- Date : {date.today().isoformat()}",
                f"- Fournisseur : `{provider}`",
                f"- Modèle configuré : `{settings.AI_MODEL}`",
                f"- Exemples évalués : {count}",
                f"- Sorties JSON valides : {valid_outputs}/{count} ({valid_outputs / count:.0%})",
                f"- Questions produites : {question_count}",
                f"- Latence moyenne : {statistics.mean(durations):.0f} ms",
                f"- Latence médiane : {statistics.median(durations):.0f} ms",
                f"- Latence p95 : {statistics.quantiles(durations, n=20)[18]:.0f} ms",
                "",
                "Matrice de confusion : non applicable, car cette commande mesure une "
                "sortie structurée et non une classification.",
                "",
                "## Lecture",
                "La validité mesurée concerne la conformité au schéma Pydantic "
                "(question, quatre choix et une bonne réponse). La pertinence "
                "pédagogique doit être relue par un formateur.",
                "",
                "Le jeu de données est volontairement court et synthétique. Il ne mesure "
                "ni la qualité pédagogique, ni la couverture de documents PDF longs.",
                "",
                "## Échecs",
                *failure_lines,
                "",
            )
        )
