"""Réglages de production, chargés dans un processus séparé : ils ne s'évaluent qu'à l'import."""

import json
import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase

READ_SETTINGS = (
    "import json, config.settings.prod as s; "
    "print(json.dumps({'hosts': s.ALLOWED_HOSTS, 'origins': s.CSRF_TRUSTED_ORIGINS, "
    "'debug': s.DEBUG, 'secure_cookies': s.SESSION_COOKIE_SECURE}))"
)


def load_prod_settings(**variables):
    environment = {
        **os.environ,
        "SECRET_KEY": "cle-de-test-pour-les-reglages-de-production",
        # Vide plutôt qu'absent : le .env local ne peut pas fournir de valeur.
        "ALLOWED_HOSTS": "",
        "RENDER_EXTERNAL_HOSTNAME": "",
        "RENDER": "",
        **variables,
    }
    return subprocess.run(
        [sys.executable, "-c", READ_SETTINGS],
        capture_output=True,
        text=True,
        env=environment,
        cwd=settings.BASE_DIR,
        check=False,
    )


class ProdSettingsTests(SimpleTestCase):
    def test_render_hostname_is_allowed_and_trusted_for_csrf(self):
        result = load_prod_settings(RENDER_EXTERNAL_HOSTNAME="skillforge.onrender.com")

        values = json.loads(result.stdout)
        self.assertEqual(values["hosts"], ["skillforge.onrender.com"])
        self.assertEqual(values["origins"], ["https://skillforge.onrender.com"])
        self.assertFalse(values["debug"])
        self.assertTrue(values["secure_cookies"])

    def test_render_build_starts_before_the_hostname_is_known(self):
        result = load_prod_settings(RENDER="true")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_hosts_outside_render_stop_the_start(self):
        result = load_prod_settings()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Définissez ALLOWED_HOSTS", result.stderr)
