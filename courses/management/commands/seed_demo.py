from django.core.management.base import BaseCommand

from accounts.models import User
from courses.models import Category, Chapter, Choice, Course, Question, Quiz


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration pour les cours."

    def handle(self, *args, **options):
        trainer, _ = User.objects.get_or_create(
            username="formateur.demo",
            defaults={
                "first_name": "Sami",
                "last_name": "Ben Amor",
                "email": "sami.benamor@skillforge.tn",
                "role": User.Role.FORMATEUR,
            },
        )
        trainer.set_password("Forge-Demo-2026")
        trainer.save()
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
        Choice.objects.get_or_create(question=question, text="Un modèle", is_correct=True)
        Choice.objects.get_or_create(question=question, text="Une URL", is_correct=False)
        self.stdout.write(self.style.SUCCESS("Données de démonstration des cours prêtes."))
