"""Données de démo des cours, appelées par « python manage.py seed_demo »."""

from accounts.models import User

from .models import Category, Chapter, Choice, Course, Question, Quiz


def seed(accounts):
    trainer = accounts[User.Role.FORMATEUR]
    category, _ = Category.objects.get_or_create(name="Développement web")
    course, _ = Course.objects.update_or_create(
        slug="django-du-modele-au-deploiement",
        defaults={
            "title": "Django : du modèle au déploiement",
            "description": "Construire une application Django testée et prête à déployer.",
            "level": Course.Level.INTERMEDIATE,
            "category": category,
            "trainer": trainer,
            "status": Course.Status.PUBLISHED,
        },
    )
    chapter, _ = Chapter.objects.get_or_create(
        course=course,
        order=1,
        defaults={
            "title": "Modéliser une fonctionnalité",
            "content": "Un modèle Django décrit les règles et les données du domaine.",
        },
    )
    quiz, _ = Quiz.objects.get_or_create(
        chapter=chapter,
        title="Vérifier les bases des modèles",
        defaults={"is_published": True},
    )
    question, _ = Question.objects.get_or_create(
        quiz=quiz,
        order=1,
        defaults={
            "statement": "Quel objet décrit une table dans Django ?",
            "explanation": "Un Model Django mappe une classe vers une table.",
            "evidence": "Un modèle Django décrit les règles et les données du domaine.",
        },
    )
    for text, is_correct in (
        ("Un modèle", True),
        ("Une URL", False),
        ("Un gabarit", False),
        ("Une migration", False),
    ):
        Choice.objects.update_or_create(
            question=question, text=text, defaults={"is_correct": is_correct}
        )
    return (
        f"{Course.objects.count()} cours, {Chapter.objects.count()} chapitres, "
        f"{Quiz.objects.count()} quiz"
    )
