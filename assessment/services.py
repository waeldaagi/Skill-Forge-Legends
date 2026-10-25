"""Contrat public du module Évaluation et preuve, appelé par les autres apps.

Version provisoire posée en Phase 0. Hamdi la remplace en Phase 3 sans changer la signature.
"""


def verified_certificates(user):
    """Certificats non révoqués de l'utilisateur.

    Provisoire : aucun certificat. En Phase 3, un QuerySet de Certificate.
    """
    return []
