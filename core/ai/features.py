from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class AIFeature:
    """Fonctionnalité IA d'un module, enregistrée dans le ready() de son AppConfig.

    run(job) appelle complete_json, applique le résultat à job.target et renvoie le JSON stocké.
    fallback(job) applique le repli métier après l'échec définitif (ex. file de modération humaine).
    mock_output(prompt) renvoie la réponse du fournisseur mock : tests, CI et démo hors ligne.
    """

    name: str
    status_message: str
    failure_message: str
    run: Callable
    fallback: Callable
    mock_output: Callable
    result_template: str = ""


_registry: dict[str, AIFeature] = {}


def register_feature(feature):
    _registry[feature.name] = feature


def get_feature(name):
    try:
        return _registry[name]
    except KeyError:
        raise LookupError(
            f"Fonctionnalité IA inconnue : « {name} ». Enregistrez-la avec register_feature()."
        ) from None
