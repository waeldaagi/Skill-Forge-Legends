"""Données de démo de la certification, appelées par « python manage.py seed_demo ».

Aucun appel à l'IA : l'avis de l'IA est écrit tel qu'une évaluation l'aurait produit.
"""

from django.conf import settings
from django.core.files.base import ContentFile

from accounts.models import Skill, User
from core.demo import create_demo_user
from courses.models import Course
from courses.services import mark_chapter_completed

from .models import AIEvaluation, Certification, Criterion, HumanReview, Submission
from .services import finalize_human_review, generate_certificate_pdf

CRITERIA = (
    ("Modélisation", "Modèles, contraintes en base et migrations cohérents.", 30),
    ("Tests", "Tests des règles métier et des permissions, couverture mesurée.", 40),
    ("Déploiement", "Réglages de production, secrets hors du code, application en ligne.", 30),
)


def seed(accounts):
    course = Course.objects.get(slug="django-du-modele-au-deploiement")
    certification, _ = Certification.objects.get_or_create(
        course=course,
        title="Django : prouver une application testée",
        defaults={
            "instructions": "Soumettez le dépôt d'une application Django testée et déployée, "
            "avec un court texte qui présente vos choix.",
            "is_active": False,
        },
    )
    for name, description, weight in CRITERIA:
        Criterion.objects.get_or_create(
            certification=certification,
            name=name,
            defaults={"description": description, "weight": weight},
        )
    # La grille est complète : la certification peut être ouverte aux apprenants.
    if not certification.is_active:
        certification.is_active = True
        certification.save(update_fields=["is_active"])

    learner = accounts[User.Role.APPRENANT]
    _make_public(learner)
    certificate = _certified_submission(certification, learner, accounts[User.Role.MENTOR])
    rania = create_demo_user("rania.bouzid", "Rania", "Bouzid", User.Role.APPRENANT)
    _pending_submission(certification, rania)
    return (
        f"Certification « {certification.title} », certificat de {learner} "
        f"({certificate.public_id}), 1 soumission à relire"
    )


def _make_public(learner):
    learner.is_public_profile = True
    learner.bio = "Apprenante Django à Tunis : API testées, déploiement sur Render."
    learner.save(update_fields=["is_public_profile", "bio"])
    for name in ("Django", "Tests"):
        learner.skills.add(Skill.objects.get_or_create(name=name)[0])


def _complete_course(learner, course):
    for chapter in course.chapters.all():
        mark_chapter_completed(learner, chapter)


def _certified_submission(certification, learner, mentor):
    _complete_course(learner, certification.course)
    submission, created = Submission.objects.get_or_create(
        learner=learner,
        certification=certification,
        attempt_number=1,
        defaults={
            "text_response": "Application de réservation de salles : modèles contraints, "
            "services testés (94 % de couverture), déploiement sur Render.",
            "repository_url": "https://github.com/waeldaagi/Skill-Forge-Legends",
            "status": Submission.Status.EVALUEE_IA,
        },
    )
    if created:
        _ai_evaluation(submission, total_score=84, scores=(80, 90, 80))
        finalize_human_review(
            submission,
            reviewer=mentor,
            final_score=84,
            decision=HumanReview.Decision.REUSSIE,
            comment="Preuve solide : tests pertinents, déploiement vérifié.",
            overrides_ai=False,
            site_url=settings.SITE_URL,
        )
    certificate = submission.certificate
    # Disque éphémère sur Render : le PDF est recréé à chaque déploiement.
    certificate.pdf.save(
        f"certificate-{certificate.public_id}.pdf",
        ContentFile(generate_certificate_pdf(certificate, settings.SITE_URL)),
        save=True,
    )
    return certificate


def _pending_submission(certification, learner):
    _complete_course(learner, certification.course)
    submission, created = Submission.objects.get_or_create(
        learner=learner,
        certification=certification,
        attempt_number=1,
        defaults={
            "text_response": "Gestion de bibliothèque en Django : modèles et vues, tests à "
            "compléter, pas encore déployée.",
            "status": Submission.Status.EVALUEE_IA,
        },
    )
    if created:
        _ai_evaluation(submission, total_score=62, scores=(70, 55, 60))


def _ai_evaluation(submission, total_score, scores):
    AIEvaluation.objects.create(
        submission=submission,
        total_score=total_score,
        criteria_scores={
            name: {"score": score, "justification": description}
            for (name, description, _weight), score in zip(CRITERIA, scores, strict=True)
        },
        strengths="Structure claire du projet.",
        improvement_axes="Ajouter des tests des permissions.",
        confidence=0.78,
        provider="démo",
    )
