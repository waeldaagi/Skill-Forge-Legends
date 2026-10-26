"""Parcours de tout le site sur les données de démo, pour chaque rôle et pour un anonyme.

Chaque lien interne affiché est suivi : une erreur 500 signale un bug, un 404 un lien cassé, un
403 un lien montré à un rôle qui n'y a pas droit.
"""

import re
from collections import deque
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import User
from core.management.commands.seed_demo import DEMO_ACCOUNTS

LINK = re.compile(r'href="(/[^"#]*)"')
# Hors du parcours : fichiers, admin Django (testé par Django), déconnexion (POST).
SKIPPED_PREFIXES = ("/static/", "/media/", "/admin/", "/comptes/deconnexion/")
MAX_PAGES_PER_PROFILE = 250
ACCEPTED_STATUSES = {200, 301, 302}


@override_settings(DEMO_PASSWORD="Parcours-Demo-2026")
class SiteCrawlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def crawl(self):
        """Renvoie les pages en anomalie : [(chemin, statut, page qui contient le lien)]."""
        queue = deque([("/", "point de départ")])
        seen = {"/"}
        problems = []
        while queue and len(seen) <= MAX_PAGES_PER_PROFILE:
            path, source = queue.popleft()
            response = self.client.get(path)
            if response.status_code not in ACCEPTED_STATUSES:
                problems.append((path, response.status_code, source))
                continue
            if response.status_code != 200 or "text/html" not in response["Content-Type"]:
                continue
            for link in LINK.findall(response.content.decode()):
                link = link.replace("&amp;", "&")
                if link not in seen and not link.startswith(SKIPPED_PREFIXES):
                    seen.add(link)
                    queue.append((link, path))
        return problems

    def test_anonymous_visitor_meets_no_broken_page(self):
        self.assertEqual(self.crawl(), [])

    def test_each_role_meets_no_broken_page(self):
        for role, (username, *_) in DEMO_ACCOUNTS.items():
            with self.subTest(role=role):
                self.client.force_login(User.objects.get(username=username))
                self.assertEqual(self.crawl(), [])
