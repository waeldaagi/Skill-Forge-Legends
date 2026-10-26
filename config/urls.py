from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from analytics.views import PilotageView
from assessment import views as assessment_views

urlpatterns = [
    path("", include("core.urls")),
    path("admin/", admin.site.urls),
    path(
        "certificats/verifier/<uuid:public_id>/",
        assessment_views.CertificateVerifyView.as_view(),
        name="certificate_verify_public",
    ),
    path(
        "api/certificats/<uuid:public_id>/",
        assessment_views.CertificateAPIView.as_view(),
        name="certificate_api_public",
    ),
    path("comptes/", include("accounts.urls")),
    path("cours/", include("courses.urls")),
    path("mentorat/", include("mentoring.urls")),
    path("communaute/", include("community.urls")),
    path("evaluation/", include("assessment.urls")),
    path("paiements/", include("payments.urls")),
    path("analytics/", include("analytics.urls")),
    path("pilotage/", PilotageView.as_view(), name="pilotage"),
]

# static() ne sert rien quand DEBUG est faux : serve() est branché directement.
if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]

handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"
