from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"
