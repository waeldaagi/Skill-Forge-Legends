from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    name = "analytics"
    verbose_name = "Pilotage et analytics"
    dashboard_panel = "analytics.dashboard.panel"
    # « Analytics IA » (modèle d'abandon, appels IA) est réservé à l'administrateur. L'apprenant,
    # dont le menu compte déjà quatre liens, ouvre « Pilotage » depuis son tableau de bord.
    role_navigation = {
        "ETABLISSEMENT": [("Pilotage", "pilotage")],
        "ADMIN": [("Pilotage", "pilotage"), ("Analytics IA", "analytics:dashboard")],
    }
