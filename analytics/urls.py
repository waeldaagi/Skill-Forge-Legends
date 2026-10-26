from django.urls import path

from .views import DashboardExportView, DashboardView

app_name = "analytics"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("export.csv", DashboardExportView.as_view(), name="export"),
]
