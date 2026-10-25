from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import DEFAULT_PASSWORD, UserFactory


class LoginLogoutTests(TestCase):
    def test_login_page_shows_the_form(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'name="username"')

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
