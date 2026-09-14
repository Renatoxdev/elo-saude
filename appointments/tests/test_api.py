from datetime import UTC, datetime, timedelta

from django.urls import reverse

from appointments.models import Appointment
from core.tests.base import AuthenticatedAPITestCase
from professionals.models import Professional
from professionals.tests.factories import professional_payload


class AppointmentAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.professional = Professional.objects.create(**professional_payload())
        self.other = Professional.objects.create(**professional_payload(social_name="Sam"))
        self.date = datetime(2020, 1, 1, 12, tzinfo=UTC)
        self.appointment = Appointment.objects.create(
            professional=self.professional, scheduled_at=self.date
        )
        self.list_url = reverse("appointment-list")
        self.detail_url = reverse("appointment-detail", args=[self.appointment.pk])

    def payload(self, **overrides):
        return {
            "professional": self.professional.pk,
            "scheduled_at": "2020-01-02T09:00:00-03:00",
            **overrides,
        }

    def test_create_past_appointment(self):
        response = self.client.post(self.list_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        appointment = Appointment.objects.get(pk=response.data["id"])
        self.assertEqual(appointment.scheduled_at, datetime(2020, 1, 2, 12, tzinfo=UTC))

    def test_list_and_detail(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["professional"], self.professional.pk)

    def test_put_changes_professional_and_time(self):
        response = self.client.put(
            self.detail_url, self.payload(professional=self.other.pk), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.professional_id, self.other.pk)
        self.assertEqual(self.appointment.scheduled_at, self.date + timedelta(days=1))

    def test_patch_and_noop_patch(self):
        for payload in ({"professional": self.other.pk}, {}):
            response = self.client.patch(self.detail_url, payload, format="json")
            self.assertEqual(response.status_code, 200, response.data)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.professional_id, self.other.pk)
        self.assertEqual(self.appointment.scheduled_at, self.date)

    def test_delete(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Appointment.objects.exists())

    def test_filter_by_professional(self):
        Appointment.objects.create(professional=self.other, scheduled_at=self.date)
        response = self.client.get(self.list_url, {"professional_id": self.professional.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.appointment.pk)
        response = self.client.get(self.list_url, {"professional_id": 999999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_invalid_filters(self):
        for value in ("abc", "-1", "1.5", "", "1 OR 1=1"):
            with self.subTest(value=value):
                response = self.client.get(self.list_url, {"professional_id": value})
                self.assertEqual(response.status_code, 400, response.data)

    def test_missing_required_fields_and_nonexistent_professional(self):
        for payload in (
            {},
            {"professional": self.professional.pk},
            {"scheduled_at": "2020-01-02T12:00:00Z"},
            self.payload(professional=999999),
        ):
            response = self.client.post(self.list_url, payload, format="json")
            self.assertEqual(response.status_code, 400, response.data)

    def test_invalid_and_naive_dates(self):
        for date in (
            "2020-01-02",
            "2020-01-02T09:00:00",
            "2020-02-31T12:00:00Z",
            "invalid",
            None,
            123,
        ):
            with self.subTest(date=date):
                response = self.client.post(
                    self.list_url, self.payload(scheduled_at=date), format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)

    def test_duplicate_instant_is_conflict_on_create_and_patch(self):
        for date in ("2020-01-01T12:00:00Z", "2020-01-01T09:00:00-03:00"):
            response = self.client.post(
                self.list_url, self.payload(scheduled_at=date), format="json"
            )
            self.assertEqual(response.status_code, 409, response.data)
        other = Appointment.objects.create(professional=self.other, scheduled_at=self.date)
        response = self.client.patch(
            reverse("appointment-detail", args=[other.pk]),
            {"professional": self.professional.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        other.refresh_from_db()
        self.assertEqual(other.professional_id, self.other.pk)

    def test_professional_with_appointments_cannot_be_deleted(self):
        response = self.client.delete(reverse("professional-detail", args=[self.professional.pk]))
        self.assertEqual(response.status_code, 409, response.data)
        self.assertTrue(Professional.objects.filter(pk=self.professional.pk).exists())
        self.assertTrue(Appointment.objects.filter(pk=self.appointment.pk).exists())

    def test_nonexistent_ids(self):
        url = reverse("appointment-detail", args=[999999])
        for method in ("get", "put", "patch", "delete"):
            response = getattr(self.client, method)(url, {}, format="json")
            self.assertEqual(response.status_code, 404)
