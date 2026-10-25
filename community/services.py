from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Q

from accounts.models import User
from core.ai import run_ai_job

from .models import ModerationLabel, ModerationStatus, Reply, Report, Thread, Vote

# En dessous de ce seuil, même un « OK » de l'IA part en relecture humaine.
MIN_CONFIDENCE_TO_PUBLISH = 0.6
HUMAN_REVIEW_REASON = "Vérification automatique indisponible : relecture humaine nécessaire."
QUEUE_STATUSES = [ModerationStatus.EN_ATTENTE, ModerationStatus.SIGNALE]


class CommunityError(Exception):
    """Règle du forum non respectée ; le message s'affiche tel quel à l'utilisateur."""


class VoteNotAllowed(CommunityError):
    pass


class AcceptNotAllowed(CommunityError):
    pass


class ReplyNotAllowed(CommunityError):
    pass


class ReportNotAllowed(CommunityError):
    pass


# Lecture


def visible_threads(user):
    """Fils publiés, plus ceux de l'utilisateur quel que soit leur statut."""
    approved_replies = Q(replies__moderation_status=ModerationStatus.APPROUVE)
    return (
        Thread.objects.filter(Q(moderation_status=ModerationStatus.APPROUVE) | Q(author=user))
        .select_related("author")
        .annotate(reply_count=Count("replies", filter=approved_replies))
        # Ordre explicite : une requête agrégée (GROUP BY) n'applique pas Meta.ordering.
        .order_by("-created_at")
    )


def visible_replies(thread, user):
    user_vote = Vote.objects.filter(reply=OuterRef("pk"), user=user)
    return (
        thread.replies.filter(Q(moderation_status=ModerationStatus.APPROUVE) | Q(author=user))
        .select_related("author", "moderation_job")
        .annotate(vote_count=Count("votes"), has_voted=Exists(user_vote))
        .order_by("created_at")
    )


def moderation_queue():
    return {
        "threads": Thread.objects.filter(moderation_status__in=QUEUE_STATUSES).select_related(
            "author"
        ),
        "replies": Reply.objects.filter(moderation_status__in=QUEUE_STATUSES).select_related(
            "author", "thread"
        ),
        "reports": Report.objects.filter(status=Report.Status.OUVERT).select_related(
            "reporter", "thread__author", "reply__author", "reply__thread"
        ),
    }


# Publication : tout contenu créé ou modifié repasse par la modération.


@transaction.atomic
def create_thread(author, title, content):
    thread = Thread.objects.create(author=author, title=title, content=content)
    request_moderation(thread)
    return thread


@transaction.atomic
def update_thread(thread, title, content):
    thread.title = title
    thread.content = content
    request_moderation(thread)


@transaction.atomic
def create_reply(thread, author, content):
    if not thread.is_published:
        raise ReplyNotAllowed("Ce sujet n'est pas encore publié : il n'accepte pas de réponse.")
    reply = Reply.objects.create(thread=thread, author=author, content=content)
    request_moderation(reply)
    return reply


@transaction.atomic
def update_reply(reply, content):
    reply.content = content
    request_moderation(reply)


def request_moderation(post):
    """Masque le contenu et confie sa vérification à l'IA (tâche Celery)."""
    post.moderation_status = ModerationStatus.EN_ATTENTE
    post.moderation_label = ""
    post.moderation_confidence = None
    post.moderation_reason = ""
    post.moderation_job = run_ai_job("moderation", post.author, target=post)
    post.save()


def apply_ai_verdict(post, label, confidence, reason):
    publish = label == ModerationLabel.OK and confidence >= MIN_CONFIDENCE_TO_PUBLISH
    post.moderation_status = ModerationStatus.APPROUVE if publish else ModerationStatus.SIGNALE
    post.moderation_label = label
    post.moderation_confidence = confidence
    post.moderation_reason = reason
    post.save(update_fields=_moderation_fields())


def keep_for_human_review(post):
    """Repli si l'IA échoue : le contenu reste masqué, jamais publié sans contrôle."""
    post.moderation_status = ModerationStatus.EN_ATTENTE
    post.moderation_reason = HUMAN_REVIEW_REASON
    post.save(update_fields=["moderation_status", "moderation_reason"])


# Décisions des modérateurs


@transaction.atomic
def approve(post):
    post.moderation_status = ModerationStatus.APPROUVE
    post.save(update_fields=["moderation_status"])
    post.reports.filter(status=Report.Status.OUVERT).update(status=Report.Status.TRAITE)


@transaction.atomic
def reject(post, reason):
    post.moderation_status = ModerationStatus.REJETE
    post.moderation_reason = reason
    post.save(update_fields=["moderation_status", "moderation_reason"])
    post.reports.filter(status=Report.Status.OUVERT).update(status=Report.Status.TRAITE)


def dismiss_report(report):
    report.status = Report.Status.TRAITE
    report.save(update_fields=["status"])


# Entraide


def toggle_vote(user, reply):
    """Ajoute ou retire le vote ; renvoie True si la réponse est désormais votée."""
    if reply.author_id == user.pk:
        raise VoteNotAllowed("Vous ne pouvez pas voter pour votre propre réponse.")
    deleted, _ = Vote.objects.filter(user=user, reply=reply).delete()
    if deleted:
        return False
    try:
        with transaction.atomic():
            Vote.objects.create(user=user, reply=reply)
    except IntegrityError:
        pass  # double clic : le premier vote est déjà enregistré
    return True


@transaction.atomic
def accept_reply(user, reply):
    thread = reply.thread
    if user.pk != thread.author_id and user.role != User.Role.MENTOR:
        raise AcceptNotAllowed("Seul l'auteur du sujet ou un mentor peut accepter une réponse.")
    if not reply.is_published:
        raise AcceptNotAllowed("Cette réponse n'est pas encore publiée.")
    thread.replies.filter(is_accepted=True).update(is_accepted=False)
    reply.is_accepted = True
    reply.save(update_fields=["is_accepted"])
    thread.is_resolved = True
    thread.save(update_fields=["is_resolved"])


def set_resolved(thread, is_resolved):
    thread.is_resolved = is_resolved
    thread.save(update_fields=["is_resolved"])


def report_post(reporter, post, reason, details):
    if post.author_id == reporter.pk:
        raise ReportNotAllowed("Vous ne pouvez pas signaler votre propre message.")
    target = {"thread": post} if isinstance(post, Thread) else {"reply": post}
    if Report.objects.filter(reporter=reporter, status=Report.Status.OUVERT, **target).exists():
        raise ReportNotAllowed("Vous avez déjà signalé ce message : un modérateur va le relire.")
    return Report.objects.create(reporter=reporter, reason=reason, details=details, **target)


def _moderation_fields():
    return ["moderation_status", "moderation_label", "moderation_confidence", "moderation_reason"]
