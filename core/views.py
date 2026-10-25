from django.http import HttpResponseServerError
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import DetailView, TemplateView

from .ai.features import get_feature
from .models import AIJob
from .permissions import OwnerRequiredMixin

CSRF_FAILURE_MESSAGE = (
    "Le formulaire a expiré ou vient d'une autre page. Rechargez la page, puis renvoyez-le."
)
# Code de réponse qui demande à HTMX d'arrêter le polling (hx-trigger="every 2s").
HTMX_STOP_POLLING = 286


class HomeView(TemplateView):
    template_name = "core/home.html"


class AIJobStatusView(OwnerRequiredMixin, DetailView):
    model = AIJob
    owner_field = "user"
    context_object_name = "job"
    template_name = "core/partials/ai_status.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(feature=get_feature(self.object.feature), **kwargs)

    def render_to_response(self, context, **response_kwargs):
        if self.object.is_finished:
            response_kwargs["status"] = HTMX_STOP_POLLING
        return super().render_to_response(context, **response_kwargs)


def permission_denied(request, exception):
    return render(request, "403.html", {"reason": str(exception)}, status=403)


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    # Sans contexte de requête : la panne vient peut-être de la base ou d'un context processor.
    return HttpResponseServerError(render_to_string("500.html"))


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", {"reason": CSRF_FAILURE_MESSAGE}, status=403)
