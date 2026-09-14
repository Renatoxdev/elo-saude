from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase


class AuthenticatedAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="operator", password="test-password-only-123"
        )

    def setUp(self):
        cache.clear()
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "operator", "password": "test-password-only-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.tokens = response.data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")
