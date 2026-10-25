from io import StringIO

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.module_loading import import_string

from accounts.models import User
from core.demo import create_demo_user

DEMO_ACCOUNTS = {
    User.Role.APPRENANT: ("yasmine.trabelsi", "Yasmine", "Trabelsi"),
    User.Role.MENTOR: ("skander.jaziri", "Skander", "Jaziri"),
    User.Role.FORMATEUR: ("mariem.gharbi", "Mariem", "Gharbi"),
    User.Role.RECRUTEUR: ("oussema.mejri", "Oussema", "Mejri"),
    User.Role.ADMIN: ("ines.hammami", "Ines", "Hammami"),
    User.Role.ETABLISSEMENT: ("khalil.chaabane", "Khalil", "Chaabane"),
}


class Command(BaseCommand):
    help = (
        "Crée un compte de démo par rôle, puis les données de démo de chaque module. "
        "Peut être relancée : rien n'est dupliqué ni supprimé."
    )

    @transaction.atomic
        "Peut être relancée : rien n'est dupliqué."
    )

    def handle(self, *args, **options):
        if not settings.DEMO_PASSWORD:
            raise CommandError(
                "DEMO_PASSWORD est vide : choisissez un mot de passe de démo dans le fichier .env."
            )
        call_command("setup_roles", stdout=StringIO())
        accounts = {
            role: create_demo_user(username, first_name, last_name, role)
            for role, (username, first_name, last_name) in DEMO_ACCOUNTS.items()
        }
        self.stdout.write(f"Comptes de démo : {len(accounts)}, un par rôle.")
        # Chaque app déclare sa fonction dans son AppConfig (attribut demo_seeder), dans l'ordre
        # d'INSTALLED_APPS : les cours existent avant les certifications qui en dépendent.
        for app_config in apps.get_app_configs():
            if seeder_path := getattr(app_config, "demo_seeder", ""):
                summary = import_string(seeder_path)(accounts)
                self.stdout.write(f"{app_config.verbose_name} : {summary}")
        self.stdout.write(self.style.SUCCESS("Données de démo prêtes."))
