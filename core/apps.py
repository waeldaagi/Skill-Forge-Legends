from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "Socle commun"

    # Lus par « setup_roles » et par le context processor de navigation.
    role_permissions = {
        "ADMIN": ["core.view_aijob", "core.view_aicalllog"],
    }
    role_navigation = {
        "ADMIN": [("Administration", "admin:index")],
    }
