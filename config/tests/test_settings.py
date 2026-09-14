import json
import os
import secrets
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


class SettingsTests(SimpleTestCase):
    def load_settings(self, module, changes=None, missing=()):
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("DJANGO_", "POSTGRES_"))
        }
        environment.update(
            DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
            DJANGO_JWT_SIGNING_KEY=secrets.token_urlsafe(64),
            DJANGO_ALLOWED_HOSTS="api.example.test",
            DJANGO_DEBUG="false",
            POSTGRES_DB="settings_test",
            POSTGRES_USER="settings_test",
            POSTGRES_PASSWORD=secrets.token_urlsafe(32),
            POSTGRES_HOST="database.example.test",
            POSTGRES_SSLMODE="require",
        )
        environment.update(changes or {})
        for key in missing:
            environment.pop(key, None)
        code = """
import importlib
import json
import sys
settings = importlib.import_module(sys.argv[1])
print(json.dumps({
    'debug': settings.DEBUG,
    'engine': settings.DATABASES['default']['ENGINE'],
    'ssl_redirect': getattr(settings, 'SECURE_SSL_REDIRECT', False),
    'session_secure': getattr(settings, 'SESSION_COOKIE_SECURE', False),
    'csrf_secure': getattr(settings, 'CSRF_COOKIE_SECURE', False),
    'cors_all': settings.CORS_ALLOW_ALL_ORIGINS,
    'proxy_header': getattr(settings, 'SECURE_PROXY_SSL_HEADER', None),
}))
"""
        return subprocess.run(
            [sys.executable, "-c", code, f"config.settings.{module}"],
            cwd=settings.BASE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def test_deployed_environments_have_secure_defaults(self):
        for module in ("staging", "production"):
            with self.subTest(module=module):
                result = self.load_settings(module)
                self.assertEqual(result.returncode, 0, result.stderr)
                values = json.loads(result.stdout)
                self.assertFalse(values["debug"])
                self.assertEqual(values["engine"], "django.db.backends.postgresql")
                self.assertTrue(values["ssl_redirect"])
                self.assertTrue(values["session_secure"])
                self.assertTrue(values["csrf_secure"])
                self.assertFalse(values["cors_all"])
                self.assertIsNone(values["proxy_header"])

    def test_deployed_environments_reject_unsafe_configuration(self):
        for module in ("staging", "production"):
            for changes in (
                {"DJANGO_DEBUG": "true"},
                {"DJANGO_SECRET_KEY": "weak"},
                {"DJANGO_SECRET_KEY": ""},
                {"DJANGO_JWT_SIGNING_KEY": "weak"},
                {"DJANGO_ALLOWED_HOSTS": ""},
                {"DJANGO_ALLOWED_HOSTS": "*"},
                {"POSTGRES_SSLMODE": "disable"},
                {"POSTGRES_PASSWORD": ""},
            ):
                with self.subTest(module=module, field=next(iter(changes))):
                    result = self.load_settings(module, changes)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("ImproperlyConfigured", result.stderr)

    def test_deployed_environments_do_not_fall_back_to_local_dotenv(self):
        for module in ("staging", "production"):
            for missing in ("DJANGO_SECRET_KEY", "POSTGRES_HOST", "POSTGRES_PASSWORD"):
                with self.subTest(module=module, missing=missing):
                    result = self.load_settings(module, missing=(missing,))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("ImproperlyConfigured", result.stderr)

    def test_local_environment_supports_http_and_postgresql(self):
        result = self.load_settings(
            "local", {"DJANGO_DEBUG": "true", "POSTGRES_SSLMODE": "disable"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertTrue(values["debug"])
        self.assertFalse(values["ssl_redirect"])
        self.assertFalse(values["cors_all"])
        self.assertEqual(values["engine"], "django.db.backends.postgresql")

    def test_proxy_trust_requires_explicit_configuration(self):
        result = self.load_settings("production", {"DJANGO_TRUST_PROXY_SSL_HEADER": "true"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["proxy_header"], ["HTTP_X_FORWARDED_PROTO", "https"]
        )
