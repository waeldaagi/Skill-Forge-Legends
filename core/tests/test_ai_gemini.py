from unittest import mock

import httpx
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from core.ai import AIServiceError, complete_json
from core.ai.prompts import INJECTION_GUARD
from core.models import AICallLog
from core.tests.fake_feature import FEATURE_NAME, LabelOutput, make_feature, registered

POST = "core.ai.providers.gemini.httpx.post"
GEMINI_ANSWER = {
    "candidates": [
        {
            "content": {"role": "model", "parts": [{"text": '{"label": "OK", "confidence": 0.8}'}]},
            "finishReason": "STOP",
        }
    ],
}
BLOCKED_PROMPT = {"promptFeedback": {"blockReason": "SAFETY"}}


def gemini_response(status=200, body=GEMINI_ANSWER):
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models")
    return httpx.Response(status, json=body, request=request)


@override_settings(AI_PROVIDER="gemini", AI_API_KEY="cle-de-test", AI_MODEL="")
class GeminiProviderTests(TestCase):
    def setUp(self):
        patcher = registered(make_feature())
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self):
        return complete_json(FEATURE_NAME, "Classe ce message.", "Bonjour à tous", LabelOutput)

    def test_request_sends_the_key_in_a_header_and_imposes_json(self):
        with mock.patch(POST, return_value=gemini_response()) as post:
            self.call()

        url, sent = post.call_args.args[0], post.call_args.kwargs
        self.assertTrue(url.endswith("/models/gemini-3.8-flash:generateContent"))
        self.assertEqual(sent["headers"], {"x-goog-api-key": "cle-de-test"})
        self.assertEqual(sent["json"]["generationConfig"], {"responseMimeType": "application/json"})
        self.assertIn(INJECTION_GUARD, sent["json"]["systemInstruction"]["parts"][0]["text"])
        self.assertEqual(sent["timeout"], 30)

    def test_answer_is_validated_and_logged_with_its_model(self):
        with mock.patch(POST, return_value=gemini_response()):
            output = self.call()

        self.assertEqual(output.label, "OK")
        log = AICallLog.objects.get()
        self.assertEqual((log.provider, log.model_name), ("gemini", "gemini-3.8-flash"))

    @override_settings(AI_MODEL="gemini-3.8-flash")
    def test_model_can_be_changed_in_the_settings(self):
        with mock.patch(POST, return_value=gemini_response()) as post:
            self.call()

        self.assertIn("/models/gemini-3.8-flash:", post.call_args.args[0])

    def test_server_error_becomes_a_retryable_service_error(self):
        with (
            mock.patch(POST, return_value=gemini_response(503, {"error": {"code": 503}})),
            self.assertLogs("core.ai.client", "WARNING"),
            self.assertRaises(AIServiceError) as raised,
        ):
            self.call()

        self.assertTrue(raised.exception.retryable)

    def test_blocked_prompt_is_treated_as_an_invalid_output(self):
        with (
            mock.patch(POST, return_value=gemini_response(body=BLOCKED_PROMPT)) as post,
            self.assertLogs("core.ai.client", "WARNING"),
            self.assertRaises(AIServiceError) as raised,
        ):
            self.call()

        self.assertEqual(raised.exception.error_type, AICallLog.ErrorType.INVALID_OUTPUT)
        self.assertEqual(post.call_count, 2)

    @override_settings(AI_API_KEY="")
    def test_missing_key_is_a_configuration_error(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "AI_API_KEY"):
            self.call()
