from typing import Protocol

from django.core.exceptions import ImproperlyConfigured

from .mock import MockProvider


class Provider(Protocol):
    """Contrat d'un fournisseur : renvoyer le texte brut du modèle.

    Il laisse remonter les exceptions httpx ; le client les traduit en AIServiceError.
    """

    name: str
    model: str

    def generate(self, *, feature: str, system: str, prompt: str, timeout: float) -> str: ...


PROVIDERS = {"mock": MockProvider}


def get_provider(name) -> Provider:
    try:
        provider_class = PROVIDERS[name]
    except KeyError:
        raise ImproperlyConfigured(
            f"AI_PROVIDER inconnu : « {name} ». Valeurs possibles : {', '.join(PROVIDERS)}."
        ) from None
    return provider_class()
