from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory


class IntegratedNavigationTests(TestCase):
    def test_each_role_sees_each_link_only_once(self):
        for role in User.Role:
            with self.subTest(role=role):
                self.client.force_login(UserFactory(role=role))
                labels = [
                    link["label"]
                    for link in self.client.get(reverse("core:home")).context["nav_links"]
                ]
                self.assertEqual(len(labels), len(set(labels)), labels)
