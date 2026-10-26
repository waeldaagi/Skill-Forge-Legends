from accounts.models import User

from .services import dashboard_metrics


def panel(user):
    # L'apprenant n'a pas de lien « Pilotage » dans le menu : il y passerait sur deux lignes.
    if user.role != User.Role.APPRENANT:
        return None
    return {
        "template": "analytics/partials/dashboard_learner.html",
        "metrics": dashboard_metrics(user),
    }
