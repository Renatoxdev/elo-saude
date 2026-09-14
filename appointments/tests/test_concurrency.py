from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connections
from django.urls import reverse
from rest_framework.test import APIClient, APITransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken

from appointments.models import Appointment
from professionals.models import Professional
from professionals.tests.factories import professional_payload


class ConcurrentAppointmentTests(APITransactionTestCase):
    def test_concurrent_requests_cannot_double_book(self):
        user = get_user_model().objects.create_user(username="concurrency")
        token = str(AccessToken.for_user(user))
        professional = Professional.objects.create(**professional_payload())
        barrier = Barrier(2)
        payload = {"professional": professional.pk, "scheduled_at": "2020-01-01T12:00:00Z"}

        def create_appointment():
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            try:
                barrier.wait(timeout=10)
                return client.post(reverse("appointment-list"), payload, format="json").status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(create_appointment) for _ in range(2)]
            statuses = sorted(future.result(timeout=15) for future in futures)
        self.assertEqual(statuses, [201, 409])
        self.assertEqual(Appointment.objects.count(), 1)
