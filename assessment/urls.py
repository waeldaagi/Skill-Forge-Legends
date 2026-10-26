from django.urls import path

from . import views

app_name = "assessment"

urlpatterns = [
    path("certifications/", views.CertificationListView.as_view(), name="certification_list"),
    path(
        "certifications/nouvelle/",
        views.CertificationCreateView.as_view(),
        name="certification_create",
    ),
    path(
        "certifications/<int:pk>/modifier/",
        views.CertificationUpdateView.as_view(),
        name="certification_update",
    ),
    path(
        "certifications/<int:pk>/supprimer/",
        views.CertificationDeleteView.as_view(),
        name="certification_delete",
    ),
    path(
        "certifications/<int:certification_pk>/criteres/nouveau/",
        views.CriterionCreateView.as_view(),
        name="criterion_create",
    ),
    path(
        "criteres/<int:pk>/modifier/", views.CriterionUpdateView.as_view(), name="criterion_update"
    ),
    path(
        "criteres/<int:pk>/supprimer/", views.CriterionDeleteView.as_view(), name="criterion_delete"
    ),
    path("catalogue/", views.CertificationCatalogView.as_view(), name="certification_catalog"),
    path(
        "catalogue/<int:certification_pk>/soumettre/",
        views.SubmissionCreateView.as_view(),
        name="submission_create",
    ),
    path("soumissions/", views.SubmissionListView.as_view(), name="submission_list"),
    path("soumissions/<int:pk>/", views.SubmissionDetailView.as_view(), name="submission_detail"),
    path("revues/", views.ReviewQueueView.as_view(), name="review_queue"),
    path("revues/<int:pk>/", views.SubmissionReviewView.as_view(), name="submission_review"),
    path("talents/", views.TalentSearchView.as_view(), name="talent_search"),
    path("talents/<int:pk>/", views.TalentProfileView.as_view(), name="talent_profile"),
    path(
        "talents/<int:pk>/contacter/", views.RecruiterContactView.as_view(), name="talent_contact"
    ),
    path(
        "certificats/verifier/<uuid:public_id>/",
        views.CertificateVerifyView.as_view(),
        name="certificate_verify",
    ),
    path(
        "api/certificats/<uuid:public_id>/",
        views.CertificateAPIView.as_view(),
        name="certificate_api",
    ),
]
