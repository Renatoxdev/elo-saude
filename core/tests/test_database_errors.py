from datetime import UTC, datetime

from django.db import IntegrityError, connection, transaction
from rest_framework.test import APITestCase

from appointments.models import Appointment
from core.exceptions import api_exception_handler
from professionals.models import Professional
from professionals.tests.factories import professional_payload


class DatabaseConflictTests(APITestCase):
    def test_postgresql_constraint_errors_become_conflicts_without_internal_details(self):
        professional = Professional.objects.create(**professional_payload())
        instant = datetime(2020, 1, 1, tzinfo=UTC)
        Appointment.objects.create(professional=professional, scheduled_at=instant)
        for professional_id in (professional.pk, professional.pk + 99999):
            with self.subTest(professional_id=professional_id):
                try:
                    with transaction.atomic():
                        Appointment.objects.create(
                            professional_id=professional_id, scheduled_at=instant
                        )
                        connection.check_constraints()
                except IntegrityError as error:
                    response = api_exception_handler(error, {})
                else:
                    self.fail("A restrição PostgreSQL deveria impedir esta gravação.")
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.data["error"]["code"], "conflict")
                self.assertNotIn("INSERT", str(response.data))
                self.assertNotIn("unique_professional_scheduled_at", str(response.data))
        self.assertEqual(Appointment.objects.count(), 1)
