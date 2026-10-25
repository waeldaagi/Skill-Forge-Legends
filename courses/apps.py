from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = "courses"
    verbose_name = "Catalogue et cours"
    demo_seeder = "courses.demo.seed"

    role_navigation = {
        "APPRENANT": [("Catalogue des cours", "courses:list")],
        "FORMATEUR": [
            ("Catalogue des cours", "courses:list"),
            ("Créer un cours", "courses:create"),
        ],
    }

    def ready(self):
        from .ai import quiz_generation

        quiz_generation.register()
