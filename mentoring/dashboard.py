from django.utils import timezone

from accounts.models import User

from .models import MentoringSession, MentorProfile, SessionStatus
from .services import free_slots

UPCOMING_SESSIONS = 3


def panel(user):
    upcoming = (
        MentoringSession.objects.filter(
            status__in=[SessionStatus.DEMANDEE, SessionStatus.CONFIRMEE],
            slot__end__gt=timezone.now(),
        )
        .select_related("slot__mentor", "learner")
        .order_by("slot__start")
    )
    if user.role == User.Role.APPRENANT:
        return {
            "template": "mentoring/partials/dashboard_learner.html",
            "sessions": upcoming.filter(learner=user)[:UPCOMING_SESSIONS],
        }
    if user.role == User.Role.MENTOR:
        mine = upcoming.filter(slot__mentor=user)
        return {
            "template": "mentoring/partials/dashboard_mentor.html",
            "sessions": mine[:UPCOMING_SESSIONS],
            "pending_count": mine.filter(status=SessionStatus.DEMANDEE).count(),
            "free_slot_count": free_slots(user).count(),
            "has_profile": MentorProfile.objects.filter(mentor=user).exists(),
        }
    return None
