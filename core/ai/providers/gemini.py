import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# AI_MODEL permet de choisir un modèle disponible dans le compte Gemini configuré.
DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiProvider:
    """API Gemini (generateContent) appelée en REST avec httpx ; la réponse est imposée en JSON."""

    name = "gemini"

    def __init__(self):
        if not settings.AI_API_KEY:
            raise ImproperlyConfigured(
                "AI_API_KEY est vide : ajoutez la clé Gemini dans le fichier .env."
            )
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL or DEFAULT_MODEL

    def generate(self, *, feature, system, prompt, timeout):
        response = httpx.post(
            API_URL.format(model=self.model),
            headers={"x-goog-api-key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=settings.AI_TIMEOUT,
        )
        response.raise_for_status()
        return candidate_text(response.json())


def candidate_text(body):
    """Texte de la première réponse proposée.

    Si Gemini bloque la demande, il ne renvoie aucune réponse : la chaîne vide sera rejetée
    par la validation pydantic, comme toute sortie inexploitable.
    """
    candidates = body.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts)
