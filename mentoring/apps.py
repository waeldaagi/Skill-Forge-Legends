from django.apps import AppConfig


class MentoringConfig(AppConfig):
    name = "mentoring"
    verbose_name = "Mentorat en direct"
    demo_seeder = "mentoring.demo.seed"
    dashboard_panel = "mentoring.dashboard.panel"

    # Lus par le context processor de navigation et par « setup_roles » (voir accounts/apps.py).
    role_navigation = {
        "APPRENANT": [
            ("Mentors", "mentoring:mentor_directory"),
            ("Mes sessions", "mentoring:session_list"),
        ],
        "MENTOR": [
            ("Mes créneaux", "mentoring:slot_list"),
            ("Mes sessions", "mentoring:session_list"),
        ],
    }
    role_permissions = {
        "MENTOR": [
            "mentoring.add_mentorprofile",
            "mentoring.change_mentorprofile",
            "mentoring.view_mentorprofile",
            "mentoring.add_availabilityslot",
            "mentoring.change_availabilityslot",
            "mentoring.delete_availabilityslot",
            "mentoring.view_availabilityslot",
            "mentoring.change_mentoringsession",
            "mentoring.view_mentoringsession",
        ],
        "APPRENANT": [
            "mentoring.view_mentorprofile",
            "mentoring.view_availabilityslot",
            "mentoring.add_mentoringsession",
            "mentoring.view_mentoringsession",
            "mentoring.add_sessionreview",
        ],
        "ADMIN": [
            "mentoring.view_mentorprofile",
            "mentoring.view_availabilityslot",
            "mentoring.view_mentoringsession",
            "mentoring.view_sessionreview",
        ],
    }
