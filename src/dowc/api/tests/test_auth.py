"""
Test that authorization is required for the API endpoints.

Test that authorization creates or gets the user.
"""
import uuid
from unittest.mock import patch

from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase
from zds_client import ClientAuth
from zgw_auth_backend.models import ApplicationCredentials
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from dowc.accounts.models import User
from dowc.accounts.tests.factories import UserFactory
from dowc.core.constants import DocFileTypes


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

    def test_create_user_during_authentication(self):
        drc_url = "https://some.drc.nl/api/v1/"
        Service.objects.create(api_type=APITypes.drc, api_root=drc_url)
        list_url = reverse_lazy("documentfile-list")

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        doc_url = f"{drc_url}enkelvoudiginformatieobjecten/{_uuid}"

        # No users exist
        self.assertEqual(User.objects.count(), 0)
        data = {
            "drc_url": doc_url,
            "purpose": DocFileTypes.read,
            "info_url": "http://www.some-referer-url.com/",
            "user_id": "some-user",
        }
        ApplicationCredentials.objects.create(client_id="dummy", secret="secret")
        auth = ClientAuth("dummy", "secret", user_id="some-user").credentials()

        response = self.client.post(
            list_url, data, HTTP_AUTHORIZATION=auth["Authorization"]
        )

        self.assertEqual(User.objects.get().username, "some-user")

    def test_update_user_during_authentication(self):
        drc_url = "https://some.drc.nl/api/v1/"
        Service.objects.create(api_type=APITypes.drc, api_root=drc_url)
        list_url = reverse_lazy("documentfile-list")

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        doc_url = f"{drc_url}enkelvoudiginformatieobjecten/{_uuid}"

        # User exists
        user = UserFactory.create(
            username="some-user", first_name="First", last_name="Last"
        )
        self.assertEqual(User.objects.count(), 1)
        data = {
            "drc_url": doc_url,
            "purpose": DocFileTypes.read,
            "info_url": "http://www.some-referer-url.com/",
        }
        ApplicationCredentials.objects.create(client_id="dummy", secret="secret")
        auth = ClientAuth(
            "dummy",
            "secret",
            user_id="some-user",
            first_name="some other first",
            last_name="some other last",
        ).credentials()

        response = self.client.post(
            list_url, data, HTTP_AUTHORIZATION=auth["Authorization"]
        )

        self.assertEqual(User.objects.get().first_name, "some other first")
