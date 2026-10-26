import logging
from pathlib import Path
from typing import Annotated

from django.db import transaction
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from core.ai import AIFeature, complete_json, delimit_user_content, register_feature
from courses.models import Choice, Question, Resource

FEATURE = "quiz_generation"
MAX_SOURCE_LENGTH = 24000
# Un chapitre accompagné de PDF produit un long prompt : Gemini peut dépasser les 30 s par défaut.
GENERATION_TIMEOUT_SECONDS = 60
logger = logging.getLogger(__name__)


# Longueur du champ Choice.text : un choix plus long serait refusé par la base.
ChoiceText = Annotated[str, Field(min_length=1, max_length=300)]


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    statement: str = Field(min_length=1)
    choices: list[ChoiceText] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=1)
    evidence: str = Field(min_length=1)

    @field_validator("choices")
    @classmethod
    def choices_are_distinct(cls, choices):
        # Deux choix identiques violeraient la contrainte unique_choice_per_question.
        if len({choice.casefold() for choice in choices}) != len(choices):
            raise ValueError("Les quatre choix d'une question doivent être différents.")
        return choices


class GeneratedQuiz(BaseModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def statements_are_distinct(self):
        statements = [question.statement.casefold() for question in self.questions]
        if len(set(statements)) != len(statements):
            raise ValueError("Deux questions du quiz ont le même énoncé.")
        return self


def run(job):
    output = complete_json(
        FEATURE,
        "Génère des questions QCM pédagogiques à partir du contenu fourni.",
        delimit_user_content(job.payload["source"]),
        GeneratedQuiz,
        timeout=GENERATION_TIMEOUT_SECONDS,
    )
    quiz = job.target
    with transaction.atomic():
        _replace_questions(quiz, output)
    return output.model_dump()


def _replace_questions(quiz, output):
    # Tout ou rien : une erreur en cours d'écriture ne laisse pas un quiz à moitié remplacé.
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
