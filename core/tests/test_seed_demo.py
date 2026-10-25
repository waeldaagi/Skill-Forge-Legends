from io import StringIO

from django.contrib.auth import authenticate
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from accounts.models import User
from core.management.commands.seed_demo import DEMO_ACCOUNTS

DEMO_PASSWORD = "Demo-Soutenance-2026"


def seed_demo():
    call_command("seed_demo", stdout=StringIO())


@override_settings(DEMO_PASSWORD=DEMO_PASSWORD)
class SeedDemoTests(TestCase):
    def test_creates_one_account_per_role_with_the_demo_password(self):
        seed_demo()

        for role, (username, _, _) in DEMO_ACCOUNTS.items():
            with self.subTest(role=role):
                user = authenticate(username=username, password=DEMO_PASSWORD)
                self.assertEqual(user.role, role)

    def test_demo_accounts_join_their_role_group(self):
        seed_demo()

        mentor = User.objects.get(username=DEMO_ACCOUNTS[User.Role.MENTOR][0])
        self.assertEqual(list(mentor.groups.values_list("name", flat=True)), ["MENTOR"])

    def test_running_twice_duplicates_nothing(self):
        seed_demo()
        user_count = User.objects.count()

        seed_demo()

        self.assertEqual(User.objects.count(), user_count)

    @override_settings(DEMO_PASSWORD="")
    def test_refuses_to_run_without_a_demo_password(self):
        with self.assertRaisesMessage(CommandError, "DEMO_PASSWORD"):
            seed_demo()
