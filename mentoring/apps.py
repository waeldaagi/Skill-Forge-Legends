from django.apps import AppConfig


class MentoringConfig(AppConfig):
    name = "mentoring"
    verbose_name = "Mentorat en direct"

    # Lu par « setup_roles » (voir accounts/apps.py).
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
