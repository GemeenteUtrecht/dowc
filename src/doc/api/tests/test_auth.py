"""
Test that authorization is required for the API endpoints.
"""
import uuid

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def test_anonymous_user(self):
        self.client.force_authenticate(user=None)

        _uuid = uuid.uuid4()
        checks = [
            ("get", reverse("documentfile-list")),
            ("post", reverse("documentfile-list")),
            ("put", reverse("documentfile-detail", kwargs={"uuid": _uuid})),
            ("patch", reverse("documentfile-detail", kwargs={"uuid": _uuid})),
        ]

        for method, path in checks:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path)

                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token(self):
        headers = {"HTTP_AUTHORIZATION": "Token 123"}

        _uuid = uuid.uuid4()
        checks = [
            ("get", reverse("documentfile-list")),
            ("post", reverse("documentfile-list")),
            ("put", reverse("documentfile-detail", kwargs={"uuid": _uuid})),
            ("patch", reverse("documentfile-detail", kwargs={"uuid": _uuid})),
        ]

        for method, path in checks:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path, **headers)

                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
