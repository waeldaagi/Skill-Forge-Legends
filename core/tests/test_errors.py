from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.urls import get_resolver, reverse
from django.utils.html import escape

from core import views


class ErrorPagesTests(TestCase):
    def test_project_handlers_are_wired(self):
        resolver = get_resolver()

        self.assertIs(resolver.resolve_error_handler(403), views.permission_denied)
        self.assertIs(resolver.resolve_error_handler(404), views.page_not_found)
        self.assertIs(resolver.resolve_error_handler(500), views.server_error)

    def test_unknown_url_shows_the_custom_404_page(self):
        response = self.client.get("/cette-page-n-existe-pas/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Page introuvable", status_code=404)

    def test_403_page_explains_the_refusal(self):
        request = RequestFactory().get("/mentorat/")
        request.user = AnonymousUser()

        response = views.permission_denied(
            request, PermissionDenied("Votre rôle ne donne pas accès à cette page.")
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Votre rôle ne donne pas accès à cette page.", status_code=403
        )

    def test_500_page_renders_without_the_request_context(self):
        response = views.server_error(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Erreur du serveur", status_code=500)

    def test_expired_form_gets_an_actionable_message(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(reverse("accounts:login"), {"username": "x", "password": "y"})

        self.assertTemplateUsed(response, "403_csrf.html")
        self.assertContains(response, escape(views.CSRF_FAILURE_MESSAGE), status_code=403)
