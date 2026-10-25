from django.contrib.auth.models import Group
from django.test import TestCase

from accounts.models import User
from accounts.tests.factories import UserFactory


class RoleGroupTests(TestCase):
    def test_new_user_joins_the_group_of_its_role(self):
        mentor = UserFactory(role=User.Role.MENTOR)

        self.assertEqual(list(mentor.groups.values_list("name", flat=True)), ["MENTOR"])

    def test_role_change_moves_user_to_the_new_role_group(self):
        user = UserFactory(role=User.Role.MENTOR)

        user.role = User.Role.FORMATEUR
        user.save()

        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["FORMATEUR"])

    def test_role_change_keeps_groups_unrelated_to_roles(self):
        user = UserFactory(role=User.Role.APPRENANT)
        beta_testers = Group.objects.create(name="Testeurs bêta")
        user.groups.add(beta_testers)

        user.role = User.Role.RECRUTEUR
        user.save()

        self.assertCountEqual(
            user.groups.values_list("name", flat=True), ["Testeurs bêta", "RECRUTEUR"]
        )

    def test_save_without_role_change_skips_group_sync(self):
        user = User.objects.get(pk=UserFactory().pk)

        with self.assertNumQueries(1):
            user.save(update_fields=["last_login"])


class StaffAccessTests(TestCase):
    def test_only_the_admin_role_opens_the_django_admin(self):
        for role in User.Role:
            with self.subTest(role=role):
                user = UserFactory(role=role)
                self.assertEqual(user.is_staff, role == User.Role.ADMIN)

    def test_losing_the_admin_role_closes_the_django_admin(self):
        user = UserFactory(role=User.Role.ADMIN)

        user.role = User.Role.MENTOR
        user.save()

        self.assertFalse(user.is_staff)

    def test_createsuperuser_produces_an_administrator(self):
        superuser = User.objects.create_superuser("direction", "direction@skillforge.test", "x")

        self.assertEqual(superuser.role, User.Role.ADMIN)
        self.assertTrue(superuser.is_staff)


class UserDisplayTests(TestCase):
    def test_str_uses_full_name(self):
        user = UserFactory.build(first_name="Mariem", last_name="Gharbi")

        self.assertEqual(str(user), "Mariem Gharbi")

    def test_str_falls_back_to_username(self):
        user = UserFactory.build(first_name="", last_name="", username="mgharbi")

        self.assertEqual(str(user), "mgharbi")
