"""Données de démo du forum, appelées par « python manage.py seed_demo ».

Les statuts de modération sont posés directement : le seed n'appelle jamais l'IA.
"""

from accounts.models import User
from core.demo import create_demo_user

from .models import ModerationStatus, Reply, Report, Thread, Vote
from .services import HUMAN_REVIEW_REASON

Role = User.Role
Status = ModerationStatus


def seed(accounts):
    yasmine = accounts[Role.APPRENANT]
    skander = accounts[Role.MENTOR]
    mariem = accounts[Role.FORMATEUR]
    rania = create_demo_user("rania.bouzid", "Rania", "Bouzid", Role.APPRENANT)
    nour = create_demo_user("nour.ayari", "Nour", "Ayari", Role.MENTOR)
    sami = create_demo_user("sami.jebali", "Sami", "Jebali", Role.APPRENANT)

    csrf = _thread(
        yasmine,
        "Erreur 403 CSRF sur un formulaire envoyé avec HTMX",
        "Mon formulaire marche en POST classique, mais renvoie 403 dès que j'ajoute hx-post. "
        "Le {% csrf_token %} est bien dans le formulaire.",
        is_resolved=True,
    )
    accepted = _reply(
        csrf,
        skander,
        "Le formulaire n'est pas envoyé tel quel par hx-post s'il est hors de l'élément. "
        'Ajoutez hx-headers=\'{"X-CSRFToken": "{{ csrf_token }}"}\' sur le body.',
        is_accepted=True,
    )
    _reply(csrf, rania, "Même problème la semaine dernière, la solution de Skander a marché.")
    for voter in (yasmine, rania, nour):
        Vote.objects.get_or_create(user=voter, reply=accepted)

    merge = _thread(
        rania,
        "Migrations en conflit après un merge de branches",
        "Deux branches ont créé une migration 0004 dans courses. makemigrations refuse de "
        "continuer. Comment s'en sortir sans perdre de données ?",
    )
    _reply(
        merge,
        nour,
        "Lancez python manage.py makemigrations --merge : Django crée une migration qui dépend "
        "des deux 0004. Vérifiez ensuite qu'aucune ne modifie le même champ.",
    )
    _reply(
        merge,
        yasmine,
        "Est-ce qu'il faut aussi supprimer la base SQLite locale après le merge ?",
        status=Status.EN_ATTENTE,
        reason=HUMAN_REVIEW_REASON,
    )

    _thread(
        mariem,
        "Ressources pour réviser les signaux Django",
        "Je prépare un chapitre sur les signaux. Quels exemples vous ont le plus aidés ?",
    )
    _thread(
        sami,
        "Corrigés des certifications à vendre",
        "Je vends les corrigés de toutes les certifications, contactez-moi en privé.",
        status=Status.SIGNALE,
        label="SPAM",
        confidence=0.97,
        reason="Vente de corrigés : publicité contraire aux règles du forum.",
    )
    rude_reply = _reply(merge, sami, "Question de débutant, lis la doc au lieu de déranger.")
    Report.objects.get_or_create(
        reporter=yasmine,
        reply=rude_reply,
        status=Report.Status.OUVERT,
        defaults={"reason": Report.Reason.TOXIQUE, "details": "Ton méprisant envers Rania."},
    )

    queue_size = (
        Thread.objects.filter(moderation_status__in=[Status.EN_ATTENTE, Status.SIGNALE]).count()
        + Reply.objects.filter(moderation_status__in=[Status.EN_ATTENTE, Status.SIGNALE]).count()
        + Report.objects.filter(status=Report.Status.OUVERT).count()
    )
    return (
        f"{Thread.objects.count()} sujets, {Reply.objects.count()} réponses, "
        f"{queue_size} éléments à modérer"
    )


def _thread(author, title, content, is_resolved=False, **moderation):
    thread, _ = Thread.objects.get_or_create(
        author=author,
        title=title,
        defaults={"content": content, "is_resolved": is_resolved, **_moderation(**moderation)},
    )
    return thread


def _reply(thread, author, content, is_accepted=False, **moderation):
    reply, _ = Reply.objects.get_or_create(
        thread=thread,
        author=author,
        content=content,
        defaults={"is_accepted": is_accepted, **_moderation(**moderation)},
    )
    return reply


def _moderation(status=Status.APPROUVE, label="OK", confidence=0.95, reason=""):
    return {
        "moderation_status": status,
        "moderation_label": label if status != Status.EN_ATTENTE else "",
        "moderation_confidence": confidence if status != Status.EN_ATTENTE else None,
        "moderation_reason": reason,
    }
