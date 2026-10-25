from unittest import mock

import redis
from django.db import OperationalError, connection
from django.test import TestCase
from django.urls import reverse

PING = "redis.Redis.ping"


class HealthCheckTests(TestCase):
    url = reverse("core:health")

    def test_reports_ok_when_database_and_redis_answer(self):
        with mock.patch(PING, return_value=True):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok", "redis": "ok"})

    def test_answers_503_when_redis_is_down(self):
        with (
            mock.patch(PING, side_effect=redis.ConnectionError("connexion refusée")),
            self.assertLogs("core.views", "WARNING"),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["redis"], "error")

    def test_answers_503_when_the_database_is_down(self):
        with (
            mock.patch(PING, return_value=True),
            mock.patch.object(
                connection, "ensure_connection", side_effect=OperationalError("base arrêtée")
            ),
            self.assertLogs("core.views", "WARNING"),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "error")

    def test_response_is_never_cached(self):
        with mock.patch(PING, return_value=True):
            response = self.client.get(self.url)

        self.assertIn("no-cache", response["Cache-Control"])
