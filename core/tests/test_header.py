from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import UserFactory


class HeaderTests(TestCase):
    def test_user_name_in_the_header_leads_to_the_profile(self):
        user = UserFactory(first_name="Ines", last_name="Hammami")
        self.client.force_login(user)

        response = self.client.get(reverse("core:home"))

        self.assertContains(
            response,
            f'<a class="sf-user__name" href="{reverse("accounts:profile")}">'
            '<span class="visually-hidden">Mon profil : </span>Ines Hammami</a>',
            html=True,
        )
