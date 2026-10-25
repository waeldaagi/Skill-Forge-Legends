"""Socle IA commun : toutes les fonctionnalités IA du projet passent par ces fonctions."""

from .client import complete_json
from .exceptions import AIServiceError
from .features import AIFeature, register_feature
from .jobs import run_ai_job
from .prompts import delimit_user_content

__all__ = [
    "AIFeature",
    "AIServiceError",
    "complete_json",
    "delimit_user_content",
    "register_feature",
    "run_ai_job",
]
