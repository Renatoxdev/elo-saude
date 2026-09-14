from datetime import UTC, datetime, timedelta, timezone

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from appointments.models import Appointment
from professionals.models import Professional
from professionals.tests.factories import professional_payload


class DomainTests(TestCase):
    def setUp(self):
        self.professional = Professional.objects.create(**professional_payload())
        self.date = datetime(2020, 1, 1, 12, tzinfo=UTC)

    def test_past_appointment_is_valid_and_prevents_professional_deletion(self):
        appointment = Appointment(professional=self.professional, scheduled_at=self.date)
        appointment.full_clean()
        appointment.save()
        with self.assertRaises(ProtectedError):
            self.professional.delete()
        appointment.delete()
        self.professional.delete()
        self.assertFalse(Professional.objects.exists())

    def test_database_rejects_same_instant_with_different_timezone(self):
        Appointment.objects.create(professional=self.professional, scheduled_at=self.date)
        equivalent = self.date.astimezone(timezone(timedelta(hours=-3)))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(professional=self.professional, scheduled_at=equivalent)

    def test_database_rejects_nonexistent_professional(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(professional_id=999999, scheduled_at=self.date)
            from django.db import connection

            connection.check_constraints()

    def test_same_time_is_allowed_for_different_professionals(self):
        other = Professional.objects.create(**professional_payload(social_name="Sam"))
        for professional in (self.professional, other):
            Appointment.objects.create(professional=professional, scheduled_at=self.date)
        self.assertEqual(Appointment.objects.count(), 2)

    def test_model_validation_rejects_naive_datetime(self):
        appointment = Appointment(
            professional=self.professional, scheduled_at=self.date.replace(tzinfo=None)
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_professional_normalizes_phone_and_cep(self):
        self.professional.contact_phone = "(11) 91234-5678"
        self.professional.postal_code = "01001-000"
        self.professional.full_clean()
        self.assertEqual(self.professional.contact_phone, "+5511912345678")
        self.assertEqual(self.professional.postal_code, "01001000")
