from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("", include("core.urls")),
    path("admin/", admin.site.urls),
    path("comptes/", include("accounts.urls")),
    path("cours/", include("courses.urls")),
    path("mentorat/", include("mentoring.urls")),
    path("communaute/", include("community.urls")),
    path("evaluation/", include("assessment.urls")),
    path("paiements/", include("payments.urls")),
    path("pilotage/", include("analytics.urls")),
]

# static() ne sert rien quand DEBUG est faux : serve() est branché directement.
if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]

handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"
