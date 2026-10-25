from datetime import timedelta
from functools import partial

from django.db import transaction
from django.db.models import Avg, Count, OuterRef, Subquery
from django.utils import timezone

from core.services import queue_email

from .models import AvailabilitySlot, MentoringSession, MentorProfile, SessionReview
from .tasks import send_session_reminder

Status = MentoringSession.Status

CANCELLATION_DEADLINE = timedelta(hours=2)
ROOM_OPENS_BEFORE = timedelta(minutes=15)
REMINDER_BEFORE = timedelta(hours=1)


class MentoringError(Exception):
    """Règle du mentorat non respectée ; le message s'affiche tel quel à l'utilisateur."""


class SlotUnavailable(MentoringError):
    pass


class SlotLocked(MentoringError):
    pass


class CancellationTooLate(MentoringError):
    pass


class InvalidSessionStatus(MentoringError):
    pass


class ReviewNotAllowed(MentoringError):
    pass


def mentor_directory():
    """Profils de mentor avec note moyenne, nombre d'avis et prochain créneau libre."""
    next_free_slot = free_slots(OuterRef("mentor")).order_by("start").values("start")[:1]
    return MentorProfile.objects.select_related("mentor").annotate(
        average_rating=Avg("mentor__availability_slots__sessions__review__rating"),
        review_count=Count("mentor__availability_slots__sessions__review"),
        next_free_slot=Subquery(next_free_slot),
    )


def free_slots(mentor):
    return AvailabilitySlot.objects.filter(mentor=mentor, is_booked=False, start__gt=timezone.now())


def ensure_slot_editable(slot):
    if slot.is_booked:
        raise SlotLocked("Ce créneau est réservé : il n'est plus modifiable ni supprimable.")


@transaction.atomic
def book_slot(learner, slot, topic, blocker_description):
    """Réserve le créneau pour l'apprenant et prévient les deux participants par e-mail."""
    # Verrou sur la ligne du créneau : si deux apprenants valident à la même seconde, le second
    # attend la fin de la transaction du premier, puis voit is_booked=True.
    slot = (
        AvailabilitySlot.objects.select_for_update(of=("self",))
        .select_related("mentor")
        .get(pk=slot.pk)
    )
    if slot.is_booked or slot.start <= timezone.now():
        raise SlotUnavailable(
            "Ce créneau vient d'être réservé ou n'est plus disponible. Choisissez-en un autre."
        )
    slot.is_booked = True
    slot.save(update_fields=["is_booked"])
    session = MentoringSession.objects.create(
        slot=slot, learner=learner, topic=topic, blocker_description=blocker_description
    )
    _notify(
        slot.mentor,
        "Nouvelle demande de session",
        f"{learner} demande une session le {slot.period}.\nSujet : {topic}\n\n"
        "Confirmez-la ou refusez-la depuis la page « Mes sessions ».",
    )
    _notify(
        learner,
        "Demande de session envoyée",
        f"Votre demande de session avec {slot.mentor} le {slot.period} est transmise.\n"
        "Vous recevrez un e-mail dès que le mentor l'aura confirmée.",
    )
    return session


@transaction.atomic
def confirm_session(session):
    _require_status(session, Status.DEMANDEE)
    session.status = Status.CONFIRMEE
    session.save(update_fields=["status", "updated_at"])
    _notify(
        session.learner,
        "Session confirmée",
        f"{session.mentor} a confirmé votre session du {session.slot.period}.\n"
        "La salle de visio ouvre 15 minutes avant le début, depuis la page de la session.",
    )
    reminder_at = session.slot.start - REMINDER_BEFORE
    if reminder_at > timezone.now():
        transaction.on_commit(
            partial(send_session_reminder.apply_async, args=[session.pk], eta=reminder_at)
        )


@transaction.atomic
def refuse_session(session, mentor_notes):
    _require_status(session, Status.DEMANDEE)
    session.status = Status.REFUSEE
    session.mentor_notes = mentor_notes
    session.save(update_fields=["status", "mentor_notes", "updated_at"])
    _release(session.slot)
    _notify(
        session.learner,
        "Demande de session refusée",
        f"{session.mentor} ne peut pas assurer la session du {session.slot.period}.\n"
        f"Motif : {mentor_notes}\n\n"
        "Vous pouvez réserver un autre créneau depuis l'annuaire.",
    )


def complete_session(session, mentor_notes):
    _require_status(session, Status.CONFIRMEE)
    if timezone.now() < session.slot.start:
        raise InvalidSessionStatus("Une session ne peut être terminée qu'après son début.")
    session.status = Status.TERMINEE
    session.mentor_notes = mentor_notes
    session.save(update_fields=["status", "mentor_notes", "updated_at"])


@transaction.atomic
def cancel_session(session):
    _require_status(session, Status.DEMANDEE, Status.CONFIRMEE)
    if session.slot.start - timezone.now() < CANCELLATION_DEADLINE:
        raise CancellationTooLate(
            "L'annulation n'est plus possible à moins de 2 h du début. Prévenez votre mentor."
        )
    session.status = Status.ANNULEE
    session.save(update_fields=["status", "updated_at"])
    _release(session.slot)
    _notify(
        session.mentor,
        "Session annulée",
        f"{session.learner} a annulé la session du {session.slot.period}.\n"
        "Le créneau est de nouveau libre dans l'annuaire.",
    )


def add_review(session, rating, comment):
    if session.status != Status.TERMINEE:
        raise ReviewNotAllowed("Vous pourrez donner votre avis une fois la session terminée.")
    if SessionReview.objects.filter(session=session).exists():
        raise ReviewNotAllowed("Vous avez déjà donné votre avis sur cette session.")
    return SessionReview.objects.create(session=session, rating=rating, comment=comment)


def room_is_open(session):
    """La salle s'ouvre 15 minutes avant le début d'une session confirmée et ferme à sa fin."""
    now = timezone.now()
    return (
        session.status == Status.CONFIRMEE
        and session.slot.start - ROOM_OPENS_BEFORE <= now <= session.slot.end
    )


def _require_status(session, *allowed):
    if session.status not in allowed:
        raise InvalidSessionStatus(
            f"Action impossible : la session est « {session.get_status_display().lower()} »."
        )


def _release(slot):
    slot.is_booked = False
    slot.save(update_fields=["is_booked"])


def _notify(user, subject, message):
    if user.email:
        queue_email(subject, message, [user.email])
