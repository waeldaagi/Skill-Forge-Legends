from io import StringIO
from unittest import mock

from django.contrib.auth.models import Group
from django.core.management import CommandError, call_command
from django.test import TestCase

from accounts.models import User

COLLECT = "accounts.management.commands.setup_roles.collect_role_permissions"


def run_setup_roles():
    call_command("setup_roles", stdout=StringIO())


class SetupRolesTests(TestCase):
    def test_creates_one_group_per_role(self):
        run_setup_roles()

        self.assertCountEqual(Group.objects.values_list("name", flat=True), User.Role.values)

    def test_gives_each_role_the_permissions_declared_by_the_apps(self):
        run_setup_roles()

        admin_group = Group.objects.get(name=User.Role.ADMIN)
        learner_group = Group.objects.get(name=User.Role.APPRENANT)
        self.assertTrue(admin_group.permissions.filter(codename="change_user").exists())
        self.assertFalse(learner_group.permissions.filter(codename="change_user").exists())

    def test_running_twice_changes_nothing(self):
        run_setup_roles()
        permission_count = Group.objects.get(name=User.Role.ADMIN).permissions.count()

        run_setup_roles()

        self.assertEqual(Group.objects.count(), len(User.Role.values))
        self.assertEqual(
            Group.objects.get(name=User.Role.ADMIN).permissions.count(), permission_count
        )

    def test_removes_permissions_no_longer_declared(self):
        run_setup_roles()

        with mock.patch(COLLECT, return_value={User.Role.ADMIN: []}):
            run_setup_roles()

        self.assertFalse(Group.objects.get(name=User.Role.ADMIN).permissions.exists())

    def test_rejects_an_unknown_permission(self):
        with (
            mock.patch(COLLECT, return_value={User.Role.ADMIN: ["accounts.fly_user"]}),
            self.assertRaisesMessage(CommandError, "accounts.fly_user"),
        ):
            run_setup_roles()

    def test_rejects_an_unknown_role(self):
        fake_config = mock.Mock(role_permissions={"STAGIAIRE": []})
        fake_config.name = "intrus"

        with (
            mock.patch("django.apps.apps.get_app_configs", return_value=[fake_config]),
            self.assertRaisesMessage(CommandError, "STAGIAIRE"),
        ):
            run_setup_roles()
