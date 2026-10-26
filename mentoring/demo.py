"""Données de démo du mentorat, appelées par « python manage.py seed_demo »."""

from datetime import timedelta

from django.utils import timezone

from accounts.models import Skill, User
from core.demo import create_demo_user
from courses.models import Course
from courses.services import enroll_learner

from .models import AvailabilitySlot, MentoringSession, MentorProfile, SessionReview

Role = User.Role
Status = MentoringSession.Status
LIVE_SESSION_TOPIC = "Démo : revue du modèle de données avant la soutenance"


def at(days, hour):
    """Jour relatif à aujourd'hui, heure pleine de Tunis."""
    moment = timezone.localtime() + timedelta(days=days)
    return moment.replace(hour=hour, minute=0, second=0, microsecond=0)


def seed(accounts):
    skander = accounts[Role.MENTOR]
    yasmine = accounts[Role.APPRENANT]
    nour = create_demo_user("nour.ayari", "Nour", "Ayari", Role.MENTOR)
    hamza = create_demo_user("hamza.khelifi", "Hamza", "Khelifi", Role.MENTOR)
    rania = create_demo_user("rania.bouzid", "Rania", "Bouzid", Role.APPRENANT)

    for mentor, title, years, skills in [
        (
            skander,
            "Développeur back-end Django et PostgreSQL",
            8,
            ["Django", "PostgreSQL", "Tests"],
        ),
        (nour, "Ingénieure DevOps : Docker, CI et déploiement", 7, ["Docker", "Déploiement"]),
        (hamza, "Développeur front-end, accessibilité web", 5, ["HTMX", "Accessibilité web"]),
    ]:
        # Un administrateur a vérifié ces mentors : sans cela, ils n'apparaîtraient pas.
        mentor.is_verified = True
        mentor.save(update_fields=["is_verified"])
        profile, _ = MentorProfile.objects.update_or_create(
            mentor=mentor, defaults={"title": title, "years_of_experience": years}
        )
        profile.expertises.set([Skill.objects.get_or_create(name=name)[0] for name in skills])

    for mentor in (skander, nour, hamza):
        for days in range(1, 7):
            for hour in (10, 14):
                _slot(mentor, at(days, hour))

    django_course = Course.objects.filter(slug="django-du-modele-au-deploiement").first()
    if django_course:
        enroll_learner(yasmine, django_course)
    confirmed = _session(
        yasmine,
        _slot(skander, at(1, 14)),
        "Erreur NoReverseMatch avec un namespace d'URL",
        "Mon template appelle {% url 'courses:detail' %} et Django lève NoReverseMatch.",
        Status.CONFIRMEE,
    )
    if django_course and confirmed.course_id is None:
        confirmed.course = django_course
        confirmed.save(update_fields=["course"])
    _session(
        yasmine,
        _slot(nour, at(2, 10)),
        "Conteneur Django qui redémarre en boucle",
        "docker compose up affiche « database is not ready » puis le conteneur web s'arrête.",
        Status.DEMANDEE,
    )
    _session(
        rania,
        _slot(skander, at(3, 10)),
        "select_related ou prefetch_related ?",
        "Ma liste de cours fait une requête par ligne ; je ne sais pas laquelle choisir.",
        Status.DEMANDEE,
    )
    past = _session(
        yasmine,
        _slot(hamza, at(-3, 18)),
        "Contraste insuffisant signalé par axe",
        "Lighthouse signale mes boutons orange sur fond blanc.",
        Status.TERMINEE,
    )
    SessionReview.objects.get_or_create(
        session=past,
        defaults={"rating": 5, "comment": "Démonstration claire avec axe, problème réglé."},
    )
    _seed_live_session(yasmine, skander)

    return (
        f"{MentorProfile.objects.count()} mentors, "
        f"{AvailabilitySlot.objects.count()} créneaux, "
        f"{MentoringSession.objects.count()} sessions"
    )


def _slot(mentor, start):
    slot, _ = AvailabilitySlot.objects.get_or_create(
        mentor=mentor, start=start, defaults={"end": start + timedelta(hours=1)}
    )
    return slot


def _session(learner, slot, topic, blocker_description, status):
    session, _ = MentoringSession.objects.get_or_create(
        slot=slot,
        learner=learner,
        defaults={"topic": topic, "blocker_description": blocker_description, "status": status},
    )
    slot.is_booked = True
    slot.save(update_fields=["is_booked"])
    return session


def _seed_live_session(learner, mentor):
    """Session confirmée qui commence dans 10 minutes : sa salle de visio est ouverte.

    Recréée à chaque lancement, car elle dépend de l'heure : lancer seed_demo juste avant la démo.
    """
    for session in MentoringSession.objects.filter(topic=LIVE_SESSION_TOPIC):
        slot = session.slot
        session.delete()
        slot.delete()
    start = timezone.now().replace(second=0, microsecond=0) + timedelta(minutes=10)
    slot = AvailabilitySlot.objects.create(
        mentor=mentor, start=start, end=start + timedelta(hours=1), is_booked=True
    )
    MentoringSession.objects.create(
        slot=slot,
        learner=learner,
        topic=LIVE_SESSION_TOPIC,
        blocker_description="Vérifier les relations et les contraintes avant la présentation.",
        status=Status.CONFIRMEE,
    )
