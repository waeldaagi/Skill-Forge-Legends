from django.http import HttpResponseServerError
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import TemplateView

CSRF_FAILURE_MESSAGE = (
    "Le formulaire a expiré ou vient d'une autre page. Rechargez la page, puis renvoyez-le."
)


class HomeView(TemplateView):
    template_name = "core/home.html"


def permission_denied(request, exception):
    return render(request, "403.html", {"reason": str(exception)}, status=403)


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    # Sans contexte de requête : la panne vient peut-être de la base ou d'un context processor.
    return HttpResponseServerError(render_to_string("500.html"))


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", {"reason": CSRF_FAILURE_MESSAGE}, status=403)
