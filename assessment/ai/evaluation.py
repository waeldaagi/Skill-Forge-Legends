import time

from django.conf import settings

from assessment import services
from core.ai import complete_json

from .prompts import SYSTEM_PROMPT, build_prompt
from .schemas import AssessmentOutput

FEATURE = "assessment_evaluation"


def mock_output(prompt):
    lower = prompt.lower()
    fraud = "copie" in lower or "plagiat" in lower
    base_score = 82 if not fraud else 45
    return {
        "total_score": base_score,
        "criteria": [
            {
                "name": "Maîtrise technique",
                "score": max(base_score - 5, 0),
                "justification": "La démarche est globalement cohérente.",
            },
            {
                "name": "Qualité de la preuve",
                "score": base_score,
                "justification": "La preuve fournie couvre le besoin annoncé.",
            },
        ],
        "strengths": ["Bonne structuration de la solution"],
        "improvement_axes": ["Détailler davantage les validations et tests"],
        "confidence": 0.72,
        "suspected_fraud": fraud,
        "fraud_reasons": ["Signal lexical de copie"] if fraud else [],
    }


def run(job):
    submission = job.target
    if submission is None:
        return {}

    criteria = [
        {"name": item.name, "description": item.description, "weight": item.weight}
        for item in submission.certification.criteria.all()
    ]
    prompt = build_prompt(
        certification_title=submission.certification.title,
        instructions=submission.certification.instructions,
        criteria=criteria,
        text_response=submission.text_response,
        repository_url=submission.repository_url,
    )

    started = time.perf_counter()
    output = complete_json(
        FEATURE,
        SYSTEM_PROMPT,
        prompt,
        AssessmentOutput,
    )
    duration_ms = round((time.perf_counter() - started) * 1000)

    criteria_scores = {
        row.name: {"score": row.score, "justification": row.justification}
        for row in output.criteria
    }
    payload = {
        "total_score": output.total_score,
        "criteria_scores": criteria_scores,
        "strengths": output.strengths,
        "improvement_axes": output.improvement_axes,
        "confidence": output.confidence,
        "suspected_fraud": output.suspected_fraud,
        "fraud_reasons": output.fraud_reasons,
    }
    services.apply_ai_evaluation(
        submission=submission,
        result=payload,
        provider=settings.AI_PROVIDER,
        duration_ms=duration_ms,
    )
    return payload


def fallback(job):
    if job.target is not None:
        services.keep_for_human_review(job.target)
