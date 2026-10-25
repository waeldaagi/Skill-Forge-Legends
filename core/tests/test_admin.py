from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from core.models import AICallLog


class AILogAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser("direction", "direction@skillforge.test", "x")
        cls.log = AICallLog.objects.create(
            feature="moderation", provider="gemini", duration_ms=1010, success=True
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_call_log_cannot_be_created_from_the_admin(self):
        response = self.client.get(reverse("admin:core_aicalllog_add"))

        self.assertEqual(response.status_code, 403)

    def test_call_log_is_shown_read_only(self):
        response = self.client.get(reverse("admin:core_aicalllog_change", args=[self.log.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')

    def test_administrator_reads_the_log_through_the_permissions_of_its_group(self):
        call_command("setup_roles", stdout=StringIO())
        self.client.force_login(UserFactory(role=User.Role.ADMIN))

        response = self.client.get(reverse("admin:core_aicalllog_changelist"))

        self.assertContains(response, "moderation")
