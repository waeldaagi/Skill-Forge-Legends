from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = "courses"
    verbose_name = "Catalogue et cours"
    demo_seeder = "courses.demo.seed"
    dashboard_panel = "courses.dashboard.panel"

    role_navigation = {
        "ANONYME": [("Catalogue des cours", "courses:list")],
        "APPRENANT": [("Catalogue des cours", "courses:list")],
        "FORMATEUR": [
            ("Catalogue des cours", "courses:list"),
            ("Mes cours", "courses:trainer_courses"),
        ],
    }

    def ready(self):
        from .ai import quiz_generation

        quiz_generation.register()
