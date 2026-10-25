from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "Socle commun"

    role_permissions = {
        "ADMIN": ["core.view_aijob", "core.view_aicalllog"],
    }
