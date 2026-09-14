import io
import os
import socket
import subprocess
import sys

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from rest_framework.test import APITestCase


class HealthTests(APITestCase):
    def test_wait_rejects_nonfinite_or_nonpositive_deadlines_without_connecting(self):
        for timeout in (float("nan"), float("inf"), float("-inf"), 0, -1):
            with self.subTest(timeout=timeout), self.assertNumQueries(0):
                with self.assertRaisesMessage(CommandError, "positivo e finito"):
                    call_command("wait_for_db", timeout=timeout)

    def test_public_health_and_head(self):
        for endpoint in ("health-live", "health-ready"):
            response = self.client.get(reverse(endpoint), HTTP_AUTHORIZATION="Bearer invalid")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {"status": "ok"})
            response = self.client.head(reverse(endpoint))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"")
            response = self.client.post(reverse(endpoint), {}, format="json")
            self.assertEqual(response.status_code, 405)
            self.assertIn("error", response.json())

    def test_wait_command_connects_to_real_database(self):
        output = io.StringIO()
        call_command("wait_for_db", timeout=2, stdout=output)
        self.assertIn("disponível", output.getvalue())

    def test_wait_command_fails_with_deadline_and_no_credentials(self):
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            environment = os.environ.copy()
            environment.update(
                POSTGRES_HOST="127.0.0.1",
                POSTGRES_PORT=str(reserved.getsockname()[1]),
                POSTGRES_CONNECT_TIMEOUT="1",
                DJANGO_SETTINGS_MODULE="config.settings.local",
            )
            result = subprocess.run(
                [sys.executable, "manage.py", "wait_for_db", "--timeout", "0.1"],
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=settings.BASE_DIR,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("indisponível", result.stderr)
        self.assertTrue(
            settings.DATABASES["default"]["PASSWORD"] not in result.stderr + result.stdout,
            "O comando não deve revelar credenciais.",
        )
