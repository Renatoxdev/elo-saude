from django.urls import reverse
from openapi_schema_validator import OAS30Validator

from core.tests.base import AuthenticatedAPITestCase
from professionals.tests.factories import professional_payload


class SchemaTests(AuthenticatedAPITestCase):
    def test_documented_examples_can_create_professional_and_appointment(self):
        professional_path = "/api/v1/professionals/"
        appointment_path = "/api/v1/appointments/"

        def example(path):
            examples = self.schema["paths"][path]["post"]["requestBody"]["content"][
                "application/json"
            ]["examples"]
            return next(iter(examples.values()))["value"].copy()

        response = self.client.post(professional_path, example(professional_path), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        payload = example(appointment_path)
        payload["professional"] = response.data["id"]
        response = self.client.post(appointment_path, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assert_contract(appointment_path, "post", response)

    def setUp(self):
        super().setUp()
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code, 200)
        self.schema = response.json()

    def assert_contract(self, path, method, response):
        specification = self.schema["paths"][path][method]["responses"][str(response.status_code)]
        OAS30Validator(
            {
                **specification["content"]["application/json"]["schema"],
                "components": self.schema["components"],
            },
            format_checker=OAS30Validator.FORMAT_CHECKER,
        ).validate(response.json())

    def test_runtime_professional_and_errors_match_schema(self):
        path = "/api/v1/professionals/"
        response = self.client.post(path, professional_payload(), format="json")
        self.assert_contract(path, "post", response)
        response = self.client.get(path)
        self.assert_contract(path, "get", response)
        response = self.client.post(path, {}, format="json")
        self.assert_contract(path, "post", response)
        self.client.credentials()
        response = self.client.get(path)
        self.assert_contract(path, "get", response)

    def test_jwt_rotated_response_and_revoke_match_schema(self):
        path = "/api/v1/auth/token/refresh/"
        response = self.client.post(path, {"refresh": self.tokens["refresh"]}, format="json")
        self.assert_contract(path, "post", response)
        self.assertIn("refresh", response.data)
        path = "/api/v1/auth/token/revoke/"
        response = self.client.post(path, {"refresh": response.data["refresh"]}, format="json")
        self.assert_contract(path, "post", response)

    def test_docs_are_public_and_assets_are_local(self):
        self.client.credentials()
        for name in ("swagger-ui", "redoc"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "/static/drf_spectacular_sidecar/")
            self.assertNotContains(response, "cdn.jsdelivr.net")
        self.assertEqual(self.client.get(reverse("schema")).status_code, 200)

    def test_domain_requires_bearer_in_schema_and_delete_has_no_body(self):
        operation = self.schema["paths"]["/api/v1/professionals/"]["get"]
        self.assertEqual(operation["security"], [{"jwtAuth": []}])
        delete = self.schema["paths"]["/api/v1/professionals/{id}/"]["delete"]
        self.assertNotIn("content", delete["responses"]["204"])
        appointment = self.schema["components"]["schemas"]["AppointmentRequest"]
        self.assertEqual(appointment["properties"]["scheduled_at"]["format"], "date-time")
