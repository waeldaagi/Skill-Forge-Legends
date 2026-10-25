import io
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from accounts.models import Etablissement, User
from accounts.tests.factories import DEFAULT_PASSWORD, UserFactory


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buffer, "PNG")
    return buffer.getvalue()


REGISTRATION = {
    "username": "mariem",
    "email": "mariem@skillforge.test",
    "first_name": "Mariem",
    "last_name": "Trabelsi",
    "role": "MENTOR",
    "password1": "Forge-Tunis-2026",
    "password2": "Forge-Tunis-2026",
}


class LoginLogoutTests(TestCase):
    def test_login_page_shows_the_form(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, reverse("accounts:register"))
        self.assertContains(response, reverse("accounts:password_reset"))

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
        response = self.client.post(reverse("accounts:register"), REGISTRATION)

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

    def test_registration_requires_an_email_address(self):
        response = self.client.post(reverse("accounts:register"), {**REGISTRATION, "email": ""})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="mariem").exists())

    def test_password_reset_sends_a_link_and_shows_the_confirmation(self):
        UserFactory(email="yasmine@skillforge.test")

        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "yasmine@skillforge.test"}
        )

        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/comptes/mot-de-passe/reinitialiser/", mail.outbox[0].body)


class ProfileTests(TestCase):
    def test_user_updates_their_profile(self):
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"first_name": "Nour", "last_name": "Ayari", "email": user.email, "bio": "Django."},
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.bio, "Django.")

    @patch("core.validators.MAX_UPLOAD_SIZE", 10)
    def test_avatar_over_the_size_limit_is_refused(self):
        # Limite abaissée : une vraie image de 5 Mo alourdirait le test sans rien prouver de plus.
        user = UserFactory()
        self.client.force_login(user)
        avatar = SimpleUploadedFile("avatar.png", png_bytes(), content_type="image/png")

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"first_name": "Nour", "last_name": "Ayari", "email": user.email, "avatar": avatar},
        )

        self.assertContains(response, "taille maximale de 5 Mo")

    def test_public_profile_is_visible_only_when_enabled(self):
        public = UserFactory(is_public_profile=True, bio="Mentor Django à Tunis.")
        private = UserFactory()

        self.assertContains(
            self.client.get(reverse("accounts:public_profile", args=[public.pk])),
            "Mentor Django à Tunis.",
        )
        self.assertEqual(
            self.client.get(reverse("accounts:public_profile", args=[private.pk])).status_code, 404
        )


class JoinInstitutionTests(TestCase):
    def setUp(self):
        self.school = Etablissement.objects.create(name="ESPRIT", city="Tunis")

    def test_learner_joins_with_the_invitation_code(self):
        learner = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(learner)

        response = self.client.post(
            reverse("accounts:join_institution"), {"invite_code": self.school.invite_code.lower()}
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        learner.refresh_from_db()
        self.assertEqual(learner.etablissement, self.school)

    def test_wrong_code_is_refused(self):
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))

        response = self.client.post(
            reverse("accounts:join_institution"), {"invite_code": "FAUX-CODE"}
        )

        self.assertContains(response, "Ce code d’invitation est invalide.")

    def test_other_roles_cannot_join_an_institution(self):
        for role in set(User.Role) - {User.Role.APPRENANT}:
            with self.subTest(role=role):
                self.client.force_login(UserFactory(role=role))

                response = self.client.get(reverse("accounts:join_institution"))

                self.assertEqual(response.status_code, 403)

    def test_join_link_is_shown_to_learners_only(self):
        join_url = reverse("accounts:join_institution")
        self.client.force_login(UserFactory(role=User.Role.APPRENANT))
        self.assertContains(self.client.get(reverse("accounts:profile")), join_url)

        self.client.force_login(UserFactory(role=User.Role.MENTOR))
        self.assertNotContains(self.client.get(reverse("accounts:profile")), join_url)
