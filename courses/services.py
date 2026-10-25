"""Contrats publics du module Catalogue et cours, appelés par les autres apps.

Version provisoire posée en Phase 0. Taha la remplace en Phase 1 sans changer les signatures.
"""


def user_can_access_course(user, course):
    """Vrai si l'utilisateur peut suivre le cours : cours gratuit, ou premium avec abonnement actif.

    Provisoire : tout cours est accessible.
    """
    return True


def course_progress(user, course):
    """Pourcentage des chapitres du cours terminés par l'utilisateur, entier de 0 à 100.

    Provisoire : aucune progression enregistrée.
    """
    return 0


def is_course_completed(user, course):
    """Vrai quand l'utilisateur a terminé tous les chapitres du cours."""
    return course_progress(user, course) == 100
