from django.apps import AppConfig


class CommunityConfig(AppConfig):
    name = "community"
    verbose_name = "Communauté"
    demo_seeder = "community.demo.seed"
    dashboard_panel = "community.dashboard.panel"

    def ready(self):
        # Enregistrement au démarrage, comme admin.site.register : le socle IA saura exécuter
        # la fonctionnalité « moderation » dans une tâche Celery.
        from core.ai import AIFeature, register_feature

        from .ai import moderation

        register_feature(
            AIFeature(
                name=moderation.FEATURE,
                status_message="Vérification automatique de votre message en cours…",
                failure_message="Un modérateur le relira avant sa publication.",
                run=moderation.run,
                fallback=moderation.fallback,
                mock_output=moderation.mock_output,
                result_template="community/partials/moderation_result.html",
            )
        )

    role_navigation = {
        "APPRENANT": [("Communauté", "community:thread_list")],
        "FORMATEUR": [("Communauté", "community:thread_list")],
        "MENTOR": [
            ("Communauté", "community:thread_list"),
            ("Modération", "community:moderation_queue"),
        ],
        "ADMIN": [
            ("Communauté", "community:thread_list"),
            ("Modération", "community:moderation_queue"),
        ],
    }
    role_permissions = {
        "APPRENANT": ["community.add_thread", "community.add_reply", "community.add_report"],
        "FORMATEUR": ["community.add_thread", "community.add_reply", "community.add_report"],
        "MENTOR": [
            "community.add_thread",
            "community.add_reply",
            "community.add_report",
            "community.view_report",
            "community.change_report",
        ],
        "ADMIN": [
            "community.view_thread",
            "community.change_thread",
            "community.view_reply",
            "community.change_reply",
            "community.view_report",
            "community.change_report",
        ],
    }
