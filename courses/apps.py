from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = "courses"
    verbose_name = "Catalogue et cours"

    role_navigation = {
        "APPRENANT": [("Catalogue des cours", "courses:list")],
        "FORMATEUR": [
            ("Catalogue des cours", "courses:list"),
            ("Créer un cours", "courses:create"),
        ],
    }
