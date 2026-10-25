from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("ia/taches/<uuid:pk>/statut/", views.AIJobStatusView.as_view(), name="ai_job_status"),
]
