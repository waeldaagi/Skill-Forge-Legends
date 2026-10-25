import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from payments.models import Plan

DEMO_PLANS = [
    {
        "slug": "gratuit",
        "name": "Gratuit",
        "price": "0.000",
        "duration_days": 365,
        "benefits": "Accès aux cours gratuits",
    },
    {
        "slug": "premium",
        "name": "Premium",
        "price": "29.900",
        "duration_days": 30,
        "benefits": "Accès aux cours premium",
    },
    {
        "slug": "pro",
        "name": "Pro",
        "price": "79.900",
        "duration_days": 90,
        "benefits": "Accès premium et accompagnement renforcé",
    },
]


class Command(BaseCommand):
    help = "Ajoute les données de démonstration sans supprimer les données existantes."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", "")
        if not password:
            raise CommandError(
                "Définissez DEMO_PASSWORD avant de lancer seed_demo "
                "(exemple : $env:DEMO_PASSWORD='...')."
            )

        for plan_data in DEMO_PLANS:
            slug = plan_data["slug"]
            plan, created = Plan.objects.update_or_create(slug=slug, defaults=plan_data)
            action = "créée" if created else "mise à jour"
            self.stdout.write(f"Offre {plan.name} {action}.")

        user, created = User.objects.get_or_create(
            username="demo_learner",
            defaults={
                "email": "demo.learner@skillforge.test",
                "first_name": "Demo",
                "last_name": "Learner",
                "role": User.Role.APPRENANT,
            },
        )
        user.email = "demo.learner@skillforge.test"
        user.role = User.Role.APPRENANT
        user.set_password(password)
        user.save()
        action = "créé" if created else "mis à jour"
        self.stdout.write(f"Utilisateur demo_learner {action}.")
        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes."))
