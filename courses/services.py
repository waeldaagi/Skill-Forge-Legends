from django.db import transaction

from payments.services import has_active_subscription

from .models import ChapterProgress, Course, Enrollment


def user_can_access_course(user, course):
    """Vérifie qu'un apprenant peut ouvrir un cours publié."""
    if not getattr(user, "is_authenticated", False) or course.status != Course.Status.PUBLISHED:
        return False
    return not course.is_premium or has_active_subscription(user)


@transaction.atomic
def enroll_learner(user, course):
    """Inscrit un apprenant une seule fois et renvoie son inscription."""
    enrollment, _ = Enrollment.objects.get_or_create(learner=user, course=course)
    return enrollment


def course_progress(user, course):
    """Renvoie le pourcentage entier de chapitres terminés pour un cours."""
    chapter_count = course.chapters.count()
    if chapter_count == 0:
        return 0
    completed_count = ChapterProgress.objects.filter(
        enrollment__learner=user, enrollment__course=course
    ).count()
    return round(completed_count * 100 / chapter_count)


def is_course_completed(user, course):
    """Vrai quand tous les chapitres d'un cours sont terminés."""
    return course_progress(user, course) == 100 and course.chapters.exists()


@transaction.atomic
def mark_chapter_completed(user, chapter):
    enrollment = enroll_learner(user, chapter.course)
    progress, _ = ChapterProgress.objects.get_or_create(enrollment=enrollment, chapter=chapter)
    return progress
