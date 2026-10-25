"""Fonctionnalité IA factice pour tester le socle sans dépendre d'un module métier."""

from typing import Literal
from unittest import mock

from pydantic import BaseModel, Field

from core.ai import AIFeature, complete_json, delimit_user_content

FEATURE_NAME = "classement_demo"


class LabelOutput(BaseModel):
    label: Literal["OK", "SPAM"]
    confidence: float = Field(ge=0, le=1)


def mock_label(prompt):
    return {"label": "SPAM" if "promo" in prompt.lower() else "OK", "confidence": 0.9}


def classify(job):
    output = complete_json(
        FEATURE_NAME,
        "Classe ce message de forum.",
        delimit_user_content(job.payload["text"]),
        LabelOutput,
    )
    return output.model_dump()


def make_feature(**overrides):
    values = {
        "name": FEATURE_NAME,
        "status_message": "Classement de votre message en cours…",
        "failure_message": "Un modérateur relira votre message.",
        "run": classify,
        "fallback": mock.Mock(),
        "mock_output": mock_label,
    }
    values.update(overrides)
    return AIFeature(**values)


def registered(feature):
    """Enregistre la fonctionnalité le temps d'un test (décorateur ou ``with``)."""
    return mock.patch.dict("core.ai.features._registry", {feature.name: feature})
