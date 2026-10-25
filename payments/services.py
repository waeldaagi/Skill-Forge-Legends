"""Contrat public du module Paiements et offres, appelé par les autres apps.

Version provisoire posée en Phase 0. Ismail la remplace en Phase 4 sans changer la signature.
"""


def has_active_subscription(user):
    """Vrai si l'utilisateur a un abonnement actif à la date du jour.

    Provisoire : True, pour que les cours premium restent accessibles pendant le développement.
    """
    return True
