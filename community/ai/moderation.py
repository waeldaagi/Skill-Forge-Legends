"""Fonctionnalité IA « moderation » : classement des messages du forum."""

import re

from core.ai import complete_json

from .. import services
from .prompts import SYSTEM_PROMPT, build_prompt
from .schemas import ModerationOutput

FEATURE = "moderation"

# Baseline sans IA : le premier groupe dont un mot apparaît l'emporte (spam, toxique, hors sujet).
KEYWORDS = {
    "SPAM": [
        "promo",
        "http",
        "https",
        "www",
        "bit.ly",
        "whatsapp",
        "gagnez",
        "gagner de l'argent",
        "remise",
        "code de réduction",
        "crypto",
        "abonnés",
        "followers",
        "achetez",
        "contactez-moi en privé",
        "offre limitée",
    ],
    "TOXIQUE": [
        "idiot",
        "débile",
        "nul",
        "stupide",
        "ferme-la",
        "ta gueule",
        "incompétent",
        "minable",
        "honte",
        "crétin",
        "abruti",
        "dégage",
    ],
    "HORS_SUJET": [
        "match",
        "foot",
        "recette",
        "couscous",
        "film",
        "série",
        "vacances",
        "météo",
        "élection",
        "mariage",
        "plage",
        "playstation",
    ],
}


# Mots entiers seulement : « nul » ne doit pas trouver « null=True » dans une question Django.
KEYWORD_PATTERNS = {
    label: re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, words)) + r")(?!\w)")
    for label, words in KEYWORDS.items()
}


def keyword_label(text):
    lowered = text.lower()
    for label, pattern in KEYWORD_PATTERNS.items():
        if pattern.search(lowered):
            return label
    return "OK"


def mock_output(prompt):
    return {
        "label": keyword_label(prompt),
        "confidence": 0.75,
        "reason": "Classement par mots-clés (fournisseur mock, sans appel à une IA).",
    }


def run(job):
    post = job.target
    if post is None:  # supprimé par son auteur avant la vérification
        return {}
    output = complete_json(
        FEATURE, SYSTEM_PROMPT, build_prompt(post.moderation_text()), ModerationOutput
    )
    services.apply_ai_verdict(post, output.label, output.confidence, output.reason)
    return output.model_dump()


def fallback(job):
    if job.target is not None:
        services.keep_for_human_review(job.target)
