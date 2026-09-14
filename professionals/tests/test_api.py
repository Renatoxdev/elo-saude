from django.urls import reverse

from core.tests.base import AuthenticatedAPITestCase
from professionals.models import Professional
from professionals.tests.factories import professional_payload


class ProfessionalAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.professional = Professional.objects.create(**professional_payload())
        self.list_url = reverse("professional-list")
        self.detail_url = reverse("professional-detail", args=[self.professional.pk])

    def test_create_normalizes_contact_and_address_and_preserves_name(self):
        payload = professional_payload(
            social_name="  D'Ávila  ", contact_phone="(11) 91234-5678", postal_code="01001-000"
        )
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        professional = Professional.objects.get(pk=response.data["id"])
        self.assertEqual(professional.social_name, "D'Ávila")
        self.assertEqual(professional.contact_phone, "+5511912345678")
        self.assertEqual(professional.postal_code, "01001000")

    def test_list_and_detail(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["social_name"], "Alex")

    def test_put_replaces_writable_fields(self):
        response = self.client.put(
            self.detail_url, professional_payload(social_name="Sam", number="123A"), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.social_name, "Sam")
        self.assertEqual(self.professional.number, "123A")

    def test_patch_preserves_other_fields(self):
        response = self.client.patch(self.detail_url, {"profession": "Enfermagem"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.profession, "Enfermagem")
        self.assertEqual(self.professional.contact_email, "alex@example.test")

    def test_delete(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(Professional.objects.filter(pk=self.professional.pk).exists())

    def test_required_fields_on_create_and_put(self):
        for field in set(professional_payload()) - {"complement"}:
            payload = professional_payload()
            payload.pop(field)
            for method, url in [("post", self.list_url), ("put", self.detail_url)]:
                with self.subTest(field=field, method=method):
                    response = getattr(self.client, method)(url, payload, format="json")
                    self.assertEqual(response.status_code, 400, response.data)
                    self.assertIn(field, response.data["error"]["details"])

    def test_invalid_fields_and_unknown_payload(self):
        for field, value in [
            ("social_name", "  "),
            ("social_name", "x" * 151),
            ("profession", ""),
            ("contact_email", "invalid"),
            ("contact_phone", "123"),
            ("contact_phone", "+12025550123"),
            ("contact_phone", "ligue 11912345678"),
            ("postal_code", "0100A000"),
            ("postal_code", "123"),
            ("state", "XX"),
            ("street", " "),
            ("number", ""),
            ("city", None),
            ("unexpected", "value"),
        ]:
            with self.subTest(field=field, value=value):
                response = self.client.post(
                    self.list_url, professional_payload(**{field: value}), format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Professional.objects.count(), 1)

    def test_nonexistent_ids(self):
        url = reverse("professional-detail", args=[999999])
        for method in ("get", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(response.status_code, 404)
                self.assertIn("error", response.data)

    def test_pagination_has_no_duplicates(self):
        Professional.objects.bulk_create(
            [Professional(**professional_payload(social_name="Alex")) for _ in range(20)]
        )
        first = self.client.get(self.list_url).data
        second = self.client.get(self.list_url, {"page": 2}).data
        self.assertEqual(first["count"], 21)
        self.assertEqual(len(first["results"]), 20)
        self.assertEqual(len(second["results"]), 1)
        self.assertTrue(
            {row["id"] for row in first["results"]}.isdisjoint(
                row["id"] for row in second["results"]
            )
        )

    def test_sql_like_name_is_stored_as_data(self):
        name = "Alex'; DROP TABLE professionals_professional; --"
        response = self.client.post(
            self.list_url, professional_payload(social_name=name), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["social_name"], name)
        self.assertEqual(Professional.objects.count(), 2)
