import json
import logging
import time

import httpx
from django.conf import settings
from pydantic import ValidationError

from core.models import AICallLog

from .exceptions import AIServiceError
from .prompts import INJECTION_GUARD
from .providers import get_provider

logger = logging.getLogger(__name__)

ErrorType = AICallLog.ErrorType

JSON_INSTRUCTIONS = (
    "Réponds uniquement par un objet JSON conforme à ce schéma, sans texte autour :\n{schema}"
)
CORRECTION_PROMPT = (
    "{prompt}\n\nTa réponse précédente était invalide :\n{previous}\n\n"
    "Erreurs : {errors}\nRenvoie uniquement l'objet JSON corrigé."
)


class _InvalidOutput(Exception):
    def __init__(self, raw, validation_error):
        super().__init__(str(validation_error))
        self.raw = raw
        self.errors = "; ".join(
            f"{'.'.join(map(str, error['loc'])) or 'racine'} : {error['msg']}"
            for error in validation_error.errors()
        )


def complete_json(feature, system, prompt, schema, timeout=30, provider_name=None):
    """Interroge le fournisseur d'IA et renvoie une instance validée du schéma pydantic.

    Une réponse invalide est redemandée une fois avec les erreurs de validation.
    Lève AIServiceError sur timeout, erreur HTTP, service injoignable ou réponse invalide.
    """
    provider = get_provider(provider_name or settings.AI_PROVIDER)
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    system = f"{system}\n\n{INJECTION_GUARD}\n\n{JSON_INSTRUCTIONS.format(schema=schema_json)}"
    try:
        return _attempt(provider, feature, system, prompt, schema, timeout)
    except _InvalidOutput as first_failure:
        retry_prompt = CORRECTION_PROMPT.format(
            prompt=prompt, previous=first_failure.raw, errors=first_failure.errors
        )
    try:
        return _attempt(provider, feature, system, retry_prompt, schema, timeout)
    except _InvalidOutput:
        raise AIServiceError(
            ErrorType.INVALID_OUTPUT,
            "La réponse du service d'IA est restée inexploitable après une relance.",
        ) from None


def _attempt(provider, feature, system, prompt, schema, timeout):
    started = time.perf_counter()
    try:
        raw = provider.generate(feature=feature, system=system, prompt=prompt, timeout=timeout)
    except httpx.HTTPError as exc:
        error = _to_service_error(exc)
        _log_call(provider, feature, started, error.error_type)
        raise error from exc
    try:
        output = schema.model_validate_json(raw)
    except ValidationError as exc:
        _log_call(provider, feature, started, ErrorType.INVALID_OUTPUT)
        raise _InvalidOutput(raw, exc) from exc
    _log_call(provider, feature, started, "")
    return output


def _to_service_error(exc):
    if isinstance(exc, httpx.TimeoutException):
        return AIServiceError(
            ErrorType.TIMEOUT, "Le service d'IA n'a pas répondu à temps.", retryable=True
        )
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 404:
            return AIServiceError(
                ErrorType.HTTP_ERROR,
                "Le modèle Gemini configuré est introuvable ou indisponible. "
                "Vérifiez AI_MODEL dans le fichier .env.",
            )
        # 429 (quota) et 5xx sont passagers ; un 4xx (clé invalide, requête refusée) ne l'est pas.
        return AIServiceError(
            ErrorType.HTTP_ERROR,
            f"Le service d'IA a renvoyé une erreur (HTTP {status}).",
            retryable=status == 429 or status >= 500,
        )
    return AIServiceError(
        ErrorType.CONNECTION_ERROR, "Le service d'IA est injoignable.", retryable=True
    )


def _log_call(provider, feature, started, error_type):
    duration_ms = round((time.perf_counter() - started) * 1000)
    if error_type:
        logger.warning("Appel IA « %s » en échec (%s, %d ms)", feature, error_type, duration_ms)
    AICallLog.objects.create(
        feature=feature,
        provider=provider.name,
        model_name=provider.model,
        duration_ms=duration_ms,
        success=not error_type,
        error_type=error_type,
    )
