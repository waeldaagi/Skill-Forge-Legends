from accounts.models import User

from .models import Course, Enrollment, Quiz
from .services import course_progress

RECENT_COURSES = 5


def panel(user):
    if user.role == User.Role.APPRENANT:
        enrollments = Enrollment.objects.filter(learner=user).select_related("course")
        recent = enrollments.order_by("-enrolled_at")[:RECENT_COURSES]
        return {
            "template": "courses/partials/dashboard_learner.html",
            "courses": [
                {"course": enrollment.course, "progress": course_progress(user, enrollment.course)}
                for enrollment in recent
            ],
        }
    if user.role == User.Role.FORMATEUR:
        courses = Course.objects.filter(trainer=user)
        return {
            "template": "courses/partials/dashboard_trainer.html",
            "published_count": courses.filter(status=Course.Status.PUBLISHED).count(),
            "draft_count": courses.filter(status=Course.Status.DRAFT).count(),
            "draft_quiz_count": Quiz.objects.filter(
                chapter__course__trainer=user, is_published=False
            ).count(),
        }
    return None
