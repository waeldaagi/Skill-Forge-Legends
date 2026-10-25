from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


def collect_role_permissions():
    """Fusionne les attributs ``role_permissions`` déclarés dans l'AppConfig de chaque app."""
    role_permissions = {role: [] for role in User.Role.values}
    for app_config in apps.get_app_configs():
        for role, dotted_names in getattr(app_config, "role_permissions", {}).items():
            if role not in role_permissions:
                raise CommandError(f"Rôle inconnu « {role} » dans {app_config.name}/apps.py.")
            role_permissions[role].extend(dotted_names)
    return role_permissions


def get_permission(dotted_name):
    app_label, codename = dotted_name.split(".")
    try:
        return Permission.objects.get(content_type__app_label=app_label, codename=codename)
    except Permission.DoesNotExist:
        raise CommandError(
            f"Permission introuvable : {dotted_name}. "
            "Vérifiez son nom ou lancez d'abord « python manage.py migrate »."
        ) from None


class Command(BaseCommand):
    help = "Crée un groupe par rôle avec ses permissions. Peut être relancée sans risque."

    def handle(self, *args, **options):
        for role, dotted_names in collect_role_permissions().items():
            group, created = Group.objects.get_or_create(name=role)
            # set() retire aussi les permissions qui ne sont plus déclarées.
            group.permissions.set([get_permission(name) for name in dotted_names])
            action = "créé" if created else "mis à jour"
            self.stdout.write(f"Groupe {role} {action} : {len(dotted_names)} permission(s).")
        self.stdout.write(self.style.SUCCESS("Groupes de rôles prêts."))
