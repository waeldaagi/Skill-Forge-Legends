from django.apps import AppConfig


class AssessmentConfig(AppConfig):
    name = "assessment"
    verbose_name = "Évaluation et preuve"
    demo_seeder = "assessment.demo.seed"

    role_navigation = {
        "APPRENANT": [("Certifications", "assessment:certification_catalog")],
        "FORMATEUR": [
            ("Certifications", "assessment:certification_list"),
            ("Revues", "assessment:review_queue"),
        ],
        "MENTOR": [("Revues", "assessment:review_queue")],
        "RECRUTEUR": [("Talents certifiés", "assessment:talent_search")],
    }

    role_permissions = {
        "APPRENANT": ["assessment.add_submission", "assessment.view_submission"],
        "FORMATEUR": [
            "assessment.add_certification",
            "assessment.change_certification",
            "assessment.delete_certification",
            "assessment.view_certification",
            "assessment.add_criterion",
            "assessment.change_criterion",
            "assessment.delete_criterion",
            "assessment.view_criterion",
            "assessment.view_submission",
            "assessment.add_humanreview",
            "assessment.change_humanreview",
            "assessment.view_humanreview",
            "assessment.view_certificate",
        ],
        "MENTOR": [
            "assessment.view_submission",
            "assessment.add_humanreview",
            "assessment.change_humanreview",
            "assessment.view_humanreview",
        ],
        "RECRUTEUR": ["assessment.view_certificate"],
        "ADMIN": [
            "assessment.view_certificate",
            "assessment.change_certificate",
            "assessment.view_humanreview",
        ],
    }

    def ready(self):
        from core.ai import AIFeature, register_feature

        from .ai import evaluation

        register_feature(
            AIFeature(
                name=evaluation.FEATURE,
                status_message="Évaluation IA en cours…",
                failure_message="La soumission attend une revue humaine.",
                run=evaluation.run,
                fallback=evaluation.fallback,
                mock_output=evaluation.mock_output,
                result_template="assessment/partials/ai_result.html",
            )
        )
