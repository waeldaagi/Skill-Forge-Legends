"""Toutes les URL nommées du projet, découvertes automatiquement : un anonyme est renvoyé vers la
connexion, sauf sur les pages publiques listées ici. Une nouvelle vue oubliée sans contrôle
d'accès fait échouer ce test.
"""

import uuid

from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from django.urls.converters import IntConverter, SlugConverter, UUIDConverter

PUBLIC_URLS = {
    "core:home",
    "core:health",
    "accounts:login",
    # POST uniquement (405 en GET) ; se déconnecter n'expose rien.
    "accounts:logout",
    "accounts:register",
    "accounts:password_reset",
    "accounts:password_reset_done",
    "accounts:password_reset_confirm",
    "accounts:password_reset_complete",
    "accounts:public_profile",
    "courses:list",
    "courses:detail",
    "payments:plans",
    # Vérification d'un certificat (QR code) : publique par nature.
    "certificate_verify_public",
    "certificate_api_public",
    "assessment:certificate_verify",
    "assessment:certificate_api",
}
# Admin Django : son propre contrôle d'accès, testé par Django.
SKIPPED_NAMESPACES = {"admin"}
SAMPLE_VALUES = {IntConverter: 1, SlugConverter: "exemple", UUIDConverter: uuid.uuid4()}


def named_urls(patterns=None, namespace=""):
    """(nom complet, kwargs d'exemple) pour chaque URL nommée."""
    for pattern in patterns if patterns is not None else get_resolver().url_patterns:
        if isinstance(pattern, URLResolver):
            child_namespace = pattern.namespace or namespace
            if child_namespace not in SKIPPED_NAMESPACES:
                prefix_kwargs = sample_kwargs(pattern)
                for name, kwargs in named_urls(pattern.url_patterns, child_namespace):
                    yield name, {**prefix_kwargs, **kwargs}
        elif isinstance(pattern, URLPattern) and pattern.name:
            full_name = f"{namespace}:{pattern.name}" if namespace else pattern.name
            yield full_name, sample_kwargs(pattern)


def sample_kwargs(pattern):
    converters = getattr(pattern.pattern, "converters", {})
    return {
        name: SAMPLE_VALUES.get(type(converter), "exemple")
        for name, converter in converters.items()
    }


class UrlProtectionTests(TestCase):
    def test_every_private_url_sends_an_anonymous_visitor_to_login(self):
        login_url = reverse("accounts:login")
        checked = 0
        for name, kwargs in named_urls():
            if name in PUBLIC_URLS:
                continue
            url = reverse(name, kwargs=kwargs)
            with self.subTest(url=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(login_url))
            checked += 1
        # Garde-fou : si la découverte échouait, le test passerait sans rien vérifier.
        self.assertGreater(checked, 60)

    def test_public_pages_answer_without_server_error(self):
        names = {name for name, _ in named_urls()}
        self.assertEqual(
            PUBLIC_URLS - names, set(), "URL publique inconnue : liste à mettre à jour"
        )
        for name, kwargs in named_urls():
            if name in PUBLIC_URLS:
                with self.subTest(url=name):
                    self.assertLess(self.client.get(reverse(name, kwargs=kwargs)).status_code, 500)
