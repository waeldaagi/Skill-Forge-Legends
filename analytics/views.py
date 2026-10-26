import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from accounts.models import User
from core.permissions import RoleRequiredMixin

from .services import dashboard_metrics, dropout_summary, export_rows


class DashboardView(RoleRequiredMixin, TemplateView):
    """Qualité du modèle d'abandon et des appels IA : un tableau de bord d'administrateur."""

    allowed_roles = (User.Role.ADMIN,)
    template_name = "analytics/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metrics"] = dashboard_metrics(self.request.user)
        context["role"] = self.request.user.get_role_display()
        context["dropout"] = dropout_summary()
        return context


class PilotageView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metrics"] = dashboard_metrics(self.request.user)
        context["role"] = self.request.user.get_role_display()
        context["chart_data"] = {
            "Abonnements actifs": context["metrics"]["active_subscriptions"],
            "Paiements réussis": context["metrics"]["successful_payments"],
            "Certificats": context["metrics"]["certificates"],
        }
        return context


class DashboardExportView(LoginRequiredMixin, View):
    def get(self, request):
        metrics = dashboard_metrics(request.user)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="skillforge-analytics.csv"'
        writer = csv.writer(response)
        writer.writerow(["Indicateur", "Valeur"])
        writer.writerows(export_rows(metrics))
        return response
