import logging
from pathlib import Path

from pydantic import BaseModel, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from core.ai import AIFeature, complete_json, delimit_user_content, register_feature
from courses.models import Choice, Question, Resource

FEATURE = "quiz_generation"
MAX_SOURCE_LENGTH = 24000
# Un chapitre accompagné de PDF produit un long prompt : Gemini peut dépasser les 30 s par défaut.
GENERATION_TIMEOUT_SECONDS = 60
logger = logging.getLogger(__name__)


class GeneratedQuestion(BaseModel):
    statement: str = Field(min_length=1)
    choices: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class GeneratedQuiz(BaseModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=10)


def run(job):
    output = complete_json(
        FEATURE,
        "Génère des questions QCM pédagogiques à partir du contenu fourni.",
        delimit_user_content(job.payload["source"]),
        GeneratedQuiz,
        timeout=GENERATION_TIMEOUT_SECONDS,
    )
    quiz = job.target
    quiz.questions.all().delete()
    for order, generated in enumerate(output.questions, start=1):
        question = Question.objects.create(
            quiz=quiz,
            order=order,
            statement=generated.statement,
            explanation=generated.explanation,
            evidence=generated.evidence,
        )
        Choice.objects.bulk_create(
            [
                Choice(question=question, text=text, is_correct=index == generated.correct_index)
                for index, text in enumerate(generated.choices)
            ]
        )
    quiz.is_ai_generated = True
    quiz.is_published = False
    quiz.save(update_fields=["is_ai_generated", "is_published"])
    return output.model_dump()


def build_chapter_source(chapter):
    sections = [f"Chapitre : {chapter.title}", chapter.content]
    resources = Resource.objects.filter(chapter=chapter).exclude(file="")
    for resource in resources:
        if Path(resource.file.name).suffix.lower() != ".pdf":
            continue
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(resource.file).pages)
        except (OSError, PdfReadError, ValueError) as exc:
            logger.warning("Impossible de lire la ressource PDF %s : %s", resource.pk, exc)
            continue
        if text.strip():
            sections.append(f"Ressource PDF « {resource.title} » :\n{text}")
    source = "\n\n".join(section for section in sections if section.strip())
    return source[:MAX_SOURCE_LENGTH]


def fallback(job):
    return None


def mock_output(prompt):
    questions = [
        {
            "statement": "Quel élément décrit les données d'une application Django ?",
            "choices": ["Un modèle", "Une URL", "Un gabarit", "Une migration"],
            "correct_index": 0,
            "explanation": "Le modèle décrit les données et leurs règles.",
            "evidence": "Le contenu du chapitre porte sur les modèles Django.",
        },
        {
            "statement": "Quel fichier associe une URL Django à une vue ?",
            "choices": ["urls.py", "models.py", "admin.py", "forms.py"],
            "correct_index": 0,
            "explanation": "Le fichier urls.py déclare les routes et les vues correspondantes.",
            "evidence": "Le contenu du chapitre présente le routage Django.",
        },
        {
            "statement": "Quel mécanisme Django applique les changements de structure de la base ?",
            "choices": ["Une migration", "Un gabarit", "Une permission", "Un formulaire"],
            "correct_index": 0,
            "explanation": "Les migrations synchronisent la structure de la base avec les modèles.",
            "evidence": "Le contenu du chapitre présente les migrations Django.",
        },
    ]
    return {
        "questions": questions,
    }


def register():
    register_feature(
        AIFeature(
            name=FEATURE,
            status_message="Génération du quiz en cours…",
            failure_message="Le quiz reste à compléter manuellement.",
            run=run,
            fallback=fallback,
            mock_output=mock_output,
        )
    )
