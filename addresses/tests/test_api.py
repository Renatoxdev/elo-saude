import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from django.test import override_settings
from django.urls import reverse

from core.tests.base import AuthenticatedAPITestCase
from professionals.tests.factories import professional_payload


class AddressHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.calls.append(self.path)
        time.sleep(self.server.delay)
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(self.server.payload)
        except BrokenPipeError:
            pass

    def log_message(self, *args):
        pass


class AddressAPITests(AuthenticatedAPITestCase):
    """Exercita HTTP real em servidor local controlado, sem depender da internet na suíte."""

    def setUp(self):
        super().setUp()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AddressHTTPHandler)
        self.server.calls = []
        self.server.status = 200
        self.server.delay = 0
        self.server.payload = json.dumps(
            {
                "cep": "01001-000",
                "logradouro": "Praça da Sé",
                "complemento": "",
                "bairro": "Sé",
                "localidade": "São Paulo",
                "uf": "SP",
            }
        ).encode()
        thread = Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.enterContext(
            override_settings(VIACEP_BASE_URL=f"http://127.0.0.1:{self.server.server_port}")
        )

    def test_lookup_normalizes_cep_and_caches_success(self):
        for cep in ("01001-000", "01001000"):
            response = self.client.get(reverse("postal_code", args=[cep]))
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["postal_code"], "01001000")
            self.assertEqual(response.data["city"], "São Paulo")
        self.assertEqual(self.server.calls, ["/01001000/json/"])

    def test_invalid_cep_does_not_make_http_request(self):
        response = self.client.get(reverse("postal_code", args=["invalid"]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.server.calls, [])

    def test_missing_postal_code_is_404(self):
        self.server.payload = b'{"erro": true}'
        response = self.client.get(reverse("postal_code", args=["99999999"]))
        self.assertEqual(response.status_code, 404)

    def test_http_error_and_invalid_response_are_503(self):
        for status, payload in (
            (503, b"{}"),
            (200, b"not-json"),
            (200, b"{}"),
            (302, b""),
            (200, b"[]"),
        ):
            self.server.status = status
            self.server.payload = payload
            response = self.client.get(reverse("postal_code", args=["01001000"]))
            self.assertEqual(response.status_code, 503, response.data)

    def test_manual_registration_does_not_depend_on_provider(self):
        self.server.status = 503
        response = self.client.post(
            reverse("professional-list"), professional_payload(), format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.server.calls, [])

    def test_oversized_or_inconsistent_provider_address_is_rejected(self):
        base = {
            "cep": "01001-000",
            "logradouro": "Praça da Sé",
            "bairro": "Sé",
            "localidade": "São Paulo",
            "uf": "SP",
        }
        for payload in (
            {**base, "logradouro": "x" * (33 * 1024)},
            {**base, "cep": "99999-999"},
            {**base, "uf": "XX"},
            {**base, "localidade": ""},
            {**base, "logradouro": None},
        ):
            self.server.payload = json.dumps(payload).encode()
            response = self.client.get(reverse("postal_code", args=["01001000"]))
            self.assertEqual(response.status_code, 503)

    def test_slow_provider_returns_503(self):
        self.server.delay = 3.2
        response = self.client.get(reverse("postal_code", args=["01001000"]))
        self.assertEqual(response.status_code, 503)
        self.assertIn("manualmente", str(response.data))

    def test_generic_postal_code_can_return_empty_street_and_neighborhood(self):
        self.server.payload = json.dumps(
            {
                "cep": "01001-000",
                "logradouro": "",
                "bairro": "",
                "localidade": "São Paulo",
                "uf": "SP",
            }
        ).encode()
        response = self.client.get(reverse("postal_code", args=["01001000"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["street"], "")
