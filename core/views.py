import logging

import redis
from django.conf import settings
from django.db import DatabaseError, connection
from django.http import HttpResponseServerError, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.generic import DetailView, TemplateView

from .ai.features import get_feature
from .dashboard import dashboard_panels
from .models import AIJob
from .permissions import OwnerRequiredMixin

logger = logging.getLogger(__name__)

CSRF_FAILURE_MESSAGE = (
    "Le formulaire a expiré ou vient d'une autre page. Rechargez la page, puis renvoyez-le."
)
# Code de réponse qui demande à HTMX d'arrêter le polling (hx-trigger="every 2s").
HTMX_STOP_POLLING = 286
REDIS_NOT_USED = "not_used"


class HomeView(TemplateView):
    """Présentation pour un visiteur ; tableau de bord de son rôle pour un utilisateur connecté."""

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["panels"] = dashboard_panels(self.request.user)
        return context


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


@never_cache
@require_GET
def health(request):
    """État de la base et de Redis, lu par le healthcheck Docker : 200 si tout répond, sinon 503."""
    # Sans worker (offre gratuite de Render), les tâches tournent dans le processus web :
    # Redis n'est pas utilisé et son absence ne rend pas le site indisponible.
    redis_state = REDIS_NOT_USED if settings.CELERY_TASK_ALWAYS_EAGER else _check_redis()
    checks = {"database": _check_database(), "redis": redis_state}
    healthy = all(state in ("ok", REDIS_NOT_USED) for state in checks.values())
    return JsonResponse(
        {"status": "ok" if healthy else "degraded", **checks}, status=200 if healthy else 503
    )


def _check_database():
    try:
        connection.ensure_connection()
    except DatabaseError as exc:
        logger.warning("Contrôle de santé : base de données injoignable (%s)", exc)
        return "error"
    return "ok"


def _check_redis():
    try:
        redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1).ping()
    except redis.RedisError as exc:
        logger.warning("Contrôle de santé : Redis injoignable (%s)", exc)
        return "error"
    return "ok"


def permission_denied(request, exception):
    return render(request, "403.html", {"reason": str(exception)}, status=403)


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    # Sans contexte de requête : la panne vient peut-être de la base ou d'un context processor.
    return HttpResponseServerError(render_to_string("500.html"))


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", {"reason": CSRF_FAILURE_MESSAGE}, status=403)
