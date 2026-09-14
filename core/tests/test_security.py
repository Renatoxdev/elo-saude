import io
import json
import logging
from contextlib import contextmanager

import jwt
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from core.logging import SafeJSONFormatter, request_context
from core.tests.base import AuthenticatedAPITestCase


@contextmanager
def capture_json_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeJSONFormatter())
    loggers = [logging.getLogger(name) for name in ("", "django", "django.server")]
    for logger in loggers:
        logger.addHandler(handler)
    try:
        yield stream
    finally:
        for logger in loggers:
            logger.removeHandler(handler)


class SecurityTests(AuthenticatedAPITestCase):
    @override_settings(ROOT_URLCONF="core.tests.urls", DEBUG=True)
    def test_logs_exclude_secrets_inputs_and_exception_messages(self):
        with capture_json_logs() as stream:
            response = self.client.get(
                "/api/failure/?password=secret-query",
                HTTP_X_REQUEST_ID="untrusted-request-id",
                HTTP_COOKIE="sessionid=secret-cookie",
            )
            self.client.get("/api/unknown-sensitive-path/")
            self.client.post(
                reverse("token_obtain_pair"),
                {"username": "secret-user", "password": "secret-password"},
                format="json",
            )
        output = stream.getvalue()
        for value in (
            self.tokens["access"],
            "secret-query",
            "secret-cookie",
            "secret-password",
            "secret-user",
            "sensitive-internal-value",
            "untrusted-request-id",
            "unknown-sensitive-path",
        ):
            self.assertNotIn(value, output)
        records = [json.loads(line) for line in output.splitlines()]
        matching = [row for row in records if row.get("request_id") == response["X-Request-ID"]]
        self.assertTrue(any(row["event"] == "api_error" for row in matching))
        access = next(row for row in matching if row["event"] == "request_completed")
        self.assertEqual(access["status_code"], 500)
        self.assertEqual(access["route"], "api/failure/")
        self.assertGreaterEqual(access["duration_ms"], 0)
        self.assertIsNone(request_context.get())

    def test_third_party_formatter_drops_arguments_extras_and_traceback_source(self):
        try:
            raise ValueError("secret-exception")
        except ValueError:
            with capture_json_logs() as stream:
                logging.getLogger("django.server").exception(
                    "Authorization %s", "secret-token", extra={"password": "secret-extra"}
                )
        output = stream.getvalue()
        self.assertNotIn("secret-", output)
        payload = json.loads(output)
        self.assertEqual(payload["exception_type"], "ValueError")
        self.assertTrue(payload["frames"])

    @override_settings(ROOT_URLCONF="core.tests.urls")
    def test_django_exception_statuses_are_preserved(self):
        for status in (400, 403, 404):
            response = self.client.get(f"/api/error/{status}/")
            self.assertEqual(response.status_code, status)
            self.assertNotIn(b"sensitive-internal-value", response.content)
            self.assertIn("error", response.json())

    def test_oversized_request_is_rejected_as_json(self):
        response = self.client.post(
            reverse("professional-list"),
            json.dumps({"social_name": "x" * (64 * 1024)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "request_too_large")
        self.assertIn("X-Request-ID", response)

    def test_forged_and_wrong_key_tokens_are_rejected(self):
        payload = jwt.decode(self.tokens["access"], options={"verify_signature": False})
        for token in (
            jwt.encode(payload, key="", algorithm="none"),
            jwt.encode(payload, key=settings.SECRET_KEY, algorithm="HS256"),
            self.tokens["refresh"],
        ):
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            response = self.client.get(reverse("professional-list"))
            self.assertEqual(response.status_code, 401)

    def test_forwarded_ip_cannot_bypass_login_throttle(self):
        for index in range(10):
            response = self.client.post(
                reverse("token_obtain_pair"),
                {},
                format="json",
                HTTP_X_FORWARDED_FOR=f"192.0.2.{index}",
            )
        self.assertEqual(response.status_code, 429)
