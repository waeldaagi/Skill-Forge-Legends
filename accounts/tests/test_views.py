from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import DEFAULT_PASSWORD, UserFactory


class LoginLogoutTests(TestCase):
    def test_login_page_shows_the_form(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, reverse("accounts:register"))

    def test_registration_page_shows_only_self_service_roles(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertTemplateUsed(response, "accounts/register.html")
        self.assertContains(response, "Apprenant")
        self.assertContains(response, "Mentor")
        self.assertContains(response, "Formateur")
        self.assertContains(response, "Recruteur")
        self.assertNotContains(response, "Administrateur")
        self.assertNotContains(response, "Établissement")

    def test_registration_creates_the_selected_role_and_logs_user_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "mariem",
                "email": "mariem@skillforge.test",
                "first_name": "Mariem",
                "last_name": "Trabelsi",
                "role": "MENTOR",
                "password1": "Forge-Tunis-2026",
                "password2": "Forge-Tunis-2026",
            },
        )

        user = UserFactory._meta.model.objects.get(username="mariem")
        self.assertRedirects(response, reverse("core:home"))
        self.assertEqual(user.role, "MENTOR")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_valid_credentials_open_a_session_and_lead_home(self):
        user = UserFactory()

        response = self.client.post(
            reverse("accounts:login"), {"username": user.username, "password": DEFAULT_PASSWORD}
        )

        self.assertRedirects(response, reverse("core:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_wrong_password_keeps_the_visitor_on_the_form(self):
        user = UserFactory()

        response = self.client.post(
            reverse("accounts:login"), {"username": user.username, "password": "mauvais"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_closes_the_session(self):
        self.client.force_login(UserFactory())

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)
