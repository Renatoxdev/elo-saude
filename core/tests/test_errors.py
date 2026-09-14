from django.test import override_settings
from django.urls import reverse

from core.tests.base import AuthenticatedAPITestCase


class APIErrorTests(AuthenticatedAPITestCase):
    def test_invalid_json_and_unsupported_content_type(self):
        url = reverse("professional-list")
        for body, content_type, status in (
            ("{broken", "application/json", 400),
            ("name=Alex", "application/x-www-form-urlencoded", 415),
            ("[]", "application/json", 400),
        ):
            response = self.client.post(url, body, content_type=content_type)
            self.assertEqual(response.status_code, status)
            self.assertIn("error", response.json())
            self.assertEqual(response["Content-Type"], "application/json")

    def test_not_acceptable_and_method_not_allowed(self):
        response = self.client.get(reverse("professional-list"), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 406)
        self.assertIn("error", response.json())
        response = self.client.put(reverse("professional-list"), {}, format="json")
        self.assertEqual(response.status_code, 405)
        self.assertIn("error", response.json())

    def test_unknown_api_route_is_json_in_local_and_deployed_modes(self):
        for debug in (True, False):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                for path in ("/api/unknown/", "/api/v1/professionals"):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 404)
                    self.assertIn("error", response.json())

    @override_settings(ROOT_URLCONF="core.tests.urls", DEBUG=False)
    def test_unexpected_errors_do_not_expose_internal_details(self):
        for url in ("/api/failure/", "/api/django-failure/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 500)
            self.assertIn("error", response.json())
            self.assertNotIn(b"sensitive-internal-value", response.content)

    @override_settings(ALLOWED_HOSTS=["allowed.test"])
    def test_invalid_host_is_json(self):
        response = self.client.get(reverse("professional-list"), HTTP_HOST="untrusted.test")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @override_settings(CORS_ALLOWED_ORIGINS=["https://frontend.example.test"])
    def test_cors_allows_only_configured_origin(self):
        url = reverse("professional-list")
        allowed = self.client.options(
            url,
            HTTP_ORIGIN="https://frontend.example.test",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )
        self.assertEqual(allowed["Access-Control-Allow-Origin"], "https://frontend.example.test")
        rejected = self.client.options(
            url,
            HTTP_ORIGIN="https://untrusted.example.test",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertNotIn("Access-Control-Allow-Origin", rejected)
