from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from core.tests.base import AuthenticatedAPITestCase


class AuthenticationTests(AuthenticatedAPITestCase):
    def test_all_domain_operations_require_authentication(self):
        self.client.credentials()
        for resource in ("professional", "appointment"):
            for method, url in (
                ("get", reverse(f"{resource}-list")),
                ("post", reverse(f"{resource}-list")),
                *[
                    (method, reverse(f"{resource}-detail", args=[1]))
                    for method in ("get", "put", "patch", "delete")
                ],
            ):
                with self.subTest(method=method, url=url):
                    response = getattr(self.client, method)(url, {}, format="json")
                    self.assertEqual(response.status_code, 401)
        self.assertEqual(
            self.client.get(reverse("postal_code", args=["01001000"])).status_code, 401
        )

    def test_invalid_expired_and_inactive_user_tokens(self):
        expired = AccessToken.for_user(self.user)
        expired.set_exp(lifetime=timedelta(seconds=-1))
        for token in ("invalid", str(expired)):
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            response = self.client.get(reverse("professional-list"))
            self.assertEqual(response.status_code, 401)
        self.user.is_active = False
        self.user.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")
        self.assertEqual(self.client.get(reverse("professional-list")).status_code, 401)

    def test_refresh_rotates_and_rejects_reuse(self):
        response = self.client.post(
            reverse("token_refresh"), {"refresh": self.tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotEqual(response.data["refresh"], self.tokens["refresh"])
        reused = self.client.post(
            reverse("token_refresh"), {"refresh": self.tokens["refresh"]}, format="json"
        )
        self.assertEqual(reused.status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.client.get(reverse("professional-list")).status_code, 200)

    def test_revoked_refresh_is_unusable(self):
        response = self.client.post(
            reverse("token_revoke"), {"refresh": self.tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("token_refresh"), {"refresh": self.tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_login_and_missing_fields(self):
        for payload, expected in (({}, 400), ({"username": "operator", "password": "wrong"}, 401)):
            response = self.client.post(reverse("token_obtain_pair"), payload, format="json")
            self.assertEqual(response.status_code, expected)
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "operator", "password": "test-password-only-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_is_throttled(self):
        for _ in range(10):
            response = self.client.post(reverse("token_obtain_pair"), {}, format="json")
        self.assertEqual(response.status_code, 429)

    def test_second_provisioned_user_has_shared_access(self):
        other = get_user_model().objects.create_user(username="other", password="another-test-123")
        token = AccessToken.for_user(other)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get(reverse("professional-list")).status_code, 200)
