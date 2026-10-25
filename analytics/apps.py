from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    name = "analytics"
    verbose_name = "Pilotage et analytics"
    role_navigation = {
        role: [("Pilotage", "pilotage"), ("Analytics IA", "analytics:dashboard")]
        for role in (
            "APPRENANT", "MENTOR", "FORMATEUR", "RECRUTEUR", "ADMIN", "ETABLISSEMENT"
        )
    }
