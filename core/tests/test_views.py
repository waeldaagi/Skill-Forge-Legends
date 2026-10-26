from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from core.context_processors import navigation


class HomeViewTests(TestCase):
    def test_home_presents_the_promise_and_the_six_actors(self):
        response = self.client.get(reverse("core:home"))

        self.assertTemplateUsed(response, "core/home.html")
        self.assertContains(response, "Être accompagné")
        for role in User.Role:
            with self.subTest(role=role):
                self.assertContains(response, f"<dt>{role.label}</dt>", html=True)

    def test_page_has_the_accessible_layout(self):
        content = self.client.get(reverse("core:home")).content.decode()

        self.assertIn('<html lang="fr">', content)
        self.assertIn('<a class="sf-skip-link" href="#contenu">Aller au contenu</a>', content)
        self.assertIn('aria-label="Navigation principale"', content)
        self.assertIn('<main id="contenu"', content)
        self.assertEqual(content.count("<h1"), 1)

    def test_anonymous_visitor_is_offered_to_log_in(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, f'href="{reverse("accounts:login")}"')
        self.assertContains(response, f'href="{reverse("accounts:register")}"')
        self.assertNotContains(response, "Se déconnecter")

    def test_anonymous_visitor_reaches_the_public_catalogue(self):
        response = self.client.get(reverse("core:home"))

        self.assertIn(
            {"label": "Cours", "url": reverse("courses:list"), "is_current": False},
            response.context["nav_links"],
        )


class RoleNavigationTests(TestCase):
    def test_administrator_sees_the_administration_link(self):
        self.client.force_login(UserFactory(role=User.Role.ADMIN))

        response = self.client.get(reverse("core:home"))

        self.assertIn(
            {"label": "Administration", "url": "/admin/", "is_current": False},
            response.context["nav_links"],
        )

    def test_learner_does_not_see_the_administration_link(self):
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))

        response = self.client.get(reverse("core:home"))

        self.assertNotContains(response, "Administration")
        self.assertContains(response, "Apprenant")

    def test_current_page_is_flagged_for_aria_current(self):
        request = RequestFactory().get("/admin/")
        request.user = UserFactory(role=User.Role.ADMIN)

        links = navigation(request)["nav_links"]

        self.assertTrue(links[0]["is_current"])
