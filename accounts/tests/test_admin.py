from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory


class UserAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(
            User.objects.create_superuser("direction", "d@skillforge.test", "x")
        )

    def test_change_page_lets_the_administrator_verify_a_mentor(self):
        mentor = UserFactory(role=User.Role.MENTOR)

        response = self.client.get(reverse("admin:accounts_user_change", args=[mentor.pk]))

        self.assertContains(response, 'name="is_verified"')
        self.assertContains(response, 'name="skills"')

    def test_user_list_can_be_filtered_on_verification(self):
        response = self.client.get(
            reverse("admin:accounts_user_changelist"), {"is_verified__exact": "0"}
        )

        self.assertEqual(response.status_code, 200)
