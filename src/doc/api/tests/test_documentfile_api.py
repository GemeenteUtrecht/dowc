import uuid

import requests_mock
from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from doc.accounts.tests.factories import UserFactory
from doc.core.models import DocumentFile


@requests_mock.Mocker()
class DocumentFileTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.DRC_URL = "https://some.drc.nl/api/v1/"
        Service.objects.create(api_type=APITypes.drc, api_root=cls.DRC_URL)
        cls.list_url = reverse_lazy("documentfile-list")
        cls.user = UserFactory.create()

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def setUpMock(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        self.test_doc_url = f"{self.DRC_URL}enkelvoudiginformatieobjecten/{_uuid}"

        # Create mock url for drc document content download
        self.test_doc_download_url = f"{self.test_doc_url}/download"

        # Create mock document data from drc
        self.doc_data = generate_oas_component(
            "drc", "schemas/EnkelvoudigInformatieObject",
        )
        self.bestandsnaam = "bestandsnaam.docx"
        self.doc_data.update(
            {
                "bestandsnaam": self.bestandsnaam,
                "inhoud": self.test_doc_download_url,
                "url": self.test_doc_url,
            }
        )

        # Create mock call for eio from DRC
        m.get(self.test_doc_url, json=self.doc_data)

        # Create fake content
        self.content = b"Beetje aan het testen."

        # Create mock call for content of eio
        m.get(self.test_doc_download_url, content=self.content)

        # Create mock url for locking of drc object
        self.test_doc_lock_url = f"{self.test_doc_url}/lock"

        # Create random lock data
        self.lock = uuid.uuid4().hex

        # Create mock call for locking of a document
        m.post(self.test_doc_lock_url, json={"lock": self.lock})

    def test_create_and_delete_document_file_through_API(self, m):
        """
        Through the API endpoints documentfile can be created and destroyed.
        This test checks if:
            1) if a POST request on the list_url creates a documentfile
            2) if a DELETE request on the documentfile-detail destroys the instance
        """

        self.setUpMock(m)
        # Prepare data for call 1
        data = {
            "drc_url": self.test_doc_url,
            "purpose": "read",
        }

        # Call 1
        response = self.client.post(self.list_url, data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("uuid", response.data)
        _uuid = response.data["uuid"]

        # Check created documentfile object
        docfile = DocumentFile.objects.filter(uuid=_uuid)
        self.assertTrue(docfile.exists())

        # Get delete url
        delete_url = reverse("documentfile-detail", kwargs={"uuid": _uuid})

        # Call delete
        response = self.client.delete(delete_url)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check if docfile exists
        self.assertFalse(DocumentFile.objects.filter(uuid=_uuid).exists())
