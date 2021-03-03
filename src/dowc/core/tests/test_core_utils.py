import uuid
from urllib.parse import urlparse

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from dowc.client import Client
from dowc.core.utils import (
    get_client,
    get_document,
    lock_document,
    unlock_document,
    update_document,
)


class GetClientTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.DRC_URL = "https://some.drc.nl/api/v1/"

    def test_fail_get_client_no_service(self):
        with self.assertRaises(RuntimeError):
            get_client("https://some-url.com")

    def test_get_client_with_service(self):
        Service.objects.create(api_type=APITypes.drc, api_root=self.DRC_URL)
        client = get_client(self.DRC_URL)
        parsed_result = urlparse(self.DRC_URL)
        self.assertEqual(client.base_path, parsed_result.path)
        self.assertTrue(type(client) is Client)


@requests_mock.Mocker()
class CoreUtilTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.DRC_URL = "https://some.drc.nl/api/v1/"

        cls.service = Service.objects.create(
            api_type=APITypes.drc, api_root=cls.DRC_URL
        )

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        cls.doc_url = f"{cls.DRC_URL}enkelvoudiginformatieobjecten/{_uuid}?versie=10"
        cls.doc_url_nonget = f"{cls.DRC_URL}enkelvoudiginformatieobjecten/{_uuid}"
        cls.doc_data = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )

    def test_get_document_with_passing_client(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")

        # Create mock document

        m.get(self.doc_url, json=self.doc_data)

        client = self.service.get_client(self.doc_url)
        response = get_document(self.doc_url, client=client)
        self.assertEqual(factory(Document, self.doc_data), response)

    def test_get_document_without_passing_client(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")

        m.get(self.doc_url, json=self.doc_data)

        response = get_document(self.doc_url)
        self.assertEqual(factory(Document, self.doc_data), response)

    def test_lock_document_with_passing_client(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")

        lock = "some-lock"
        m.post(self.doc_url_nonget + "/lock", json={"lock": lock})

        client = self.service.get_client(self.doc_url)
        response = lock_document(self.doc_url_nonget, client=client)
        self.assertEqual(lock, response)

    def test_lock_document_without_passing_client(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")

        lock = "some-lock"
        m.post(self.doc_url_nonget + "/lock", json={"lock": lock})

        response = lock_document(self.doc_url_nonget)
        self.assertEqual(lock, response)

    def test_unlock_document_with_passing_client(self, m):
        """
        No errors == pass
        """
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")

        m.post(self.doc_url_nonget + "/unlock", status_code=204)
        m.get(self.doc_url_nonget, json={**self.doc_data, "versie": 42})

        lock = "some-lock"
        client = self.service.get_client(self.doc_url)

        unlock_document(self.doc_url, lock, client=client)

    def test_unlock_document_without_passing_client(self, m):
        """
        No errors == pass
        """
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")
        m.post(self.doc_url_nonget + "/unlock", status_code=204)
        m.get(self.doc_url_nonget, json={**self.doc_data, "versie": 42})

        lock = "some-lock"

        try:
            unlock_document(self.doc_url, lock)
        except Exception:
            self.fail("Failed to unlock document")

    def test_fail_unlock_document_by_receiving_wrong_status_code(self, m):
        """
        Assertion error being raised == pass
        """
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")
        m.post(self.doc_url_nonget + "/unlock", status_code=200)

        lock = "some-lock"
        with self.assertRaises(AssertionError):
            unlock_document(self.doc_url, lock)

    def test_update_document_with_passing_client(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")
        m.patch(self.doc_url_nonget, json=self.doc_data)
        client = self.service.get_client(self.doc_url)

        response = update_document(self.doc_url, self.doc_data, client=client)

        self.assertEqual(factory(Document, self.doc_data), response)

    def test_update_document_without_passing_client(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")
        m.patch(self.doc_url_nonget, json=self.doc_data)

        response = update_document(self.doc_url, self.doc_data)

        self.assertEqual(factory(Document, self.doc_data), response)
