from pydantic import BaseModel, Field

from core.ai import AIFeature, complete_json, delimit_user_content, register_feature

from courses.models import Choice, Question

FEATURE = "quiz_generation"


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
        delimit_user_content(job.payload["chapter"]),
        GeneratedQuiz,
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


def fallback(job):
    return None


def mock_output(prompt):
    return {
        "questions": [
            {
                "statement": "Quel élément décrit les données d'une application Django ?",
                "choices": ["Un modèle", "Une URL", "Un gabarit", "Une migration"],
                "correct_index": 0,
                "explanation": "Le modèle décrit les données et leurs règles.",
                "evidence": "Le contenu du chapitre porte sur les modèles Django.",
            }
        ]
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
