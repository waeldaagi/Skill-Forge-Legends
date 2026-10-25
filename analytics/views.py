import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from .services import dashboard_metrics, dropout_summary


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metrics"] = dashboard_metrics(self.request.user)
        context["role"] = self.request.user.get_role_display()
        context["dropout"] = dropout_summary()
        context["chart_data"] = {
            "abonnements": context["metrics"]["active_subscriptions"],
            "paiements": context["metrics"]["successful_payments"],
            "certificats": context["metrics"]["certificates"],
        }
        return context


class PilotageView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metrics"] = dashboard_metrics(self.request.user)
        context["role"] = self.request.user.get_role_display()
        context["chart_data"] = {
            "abonnements": context["metrics"]["active_subscriptions"],
            "paiements": context["metrics"]["successful_payments"],
            "certificats": context["metrics"]["certificates"],
        }
        return context


class DashboardExportView(LoginRequiredMixin, View):
    def get(self, request):
        metrics = dashboard_metrics(request.user)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="skillforge-analytics.csv"'
        writer = csv.writer(response)
        writer.writerow(["Indicateur", "Valeur"])
        writer.writerows(metrics.items())
        return response
