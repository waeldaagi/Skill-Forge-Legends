from accounts.models import User

from .services import moderation_queue

MODERATORS = (User.Role.MENTOR, User.Role.ADMIN)


def panel(user):
    if user.role not in MODERATORS:
        return None
    return {
        "template": "community/partials/dashboard_moderation.html",
        "pending_count": sum(items.count() for items in moderation_queue().values()),
    }
