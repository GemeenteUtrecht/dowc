import tempfile
import uuid
from unittest import mock
from urllib.parse import urlparse

from django.conf import settings
from django.test import override_settings

import requests_mock
from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from doc.accounts.tests.factories import UserFactory
from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile
from doc.core.resource import WebDavResource
from doc.core.tokens import document_token_generator

tmpdir = tempfile.mkdtemp()

# Mock storage for test_magic_url_get
@override_settings(PRIVATE_MEDIA_ROOT=tmpdir)
def get_storage_mock():
    storage_mock = WebDavResource
    storage_mock.root = settings.PRIVATE_MEDIA_ROOT
    storage_mock.exists = True
    return storage_mock


@override_settings(PRIVATE_MEDIA_ROOT=tmpdir)
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
            "drc",
            "schemas/EnkelvoudigInformatieObject",
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
            "purpose": DocFileTypes.read,
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

    def test_magic_url(self, m):
        """
        This tests the creation of the magic url token(s).
        """
        self.setUpMock(m)

        # Prepare data
        data = {
            "drc_url": self.test_doc_url,
            "purpose": DocFileTypes.read,
        }

        response = self.client.post(self.list_url, data)
        # Check if magic url is kicked back
        self.assertIn("magic_url", response.data)
        magic_url = response.data["magic_url"]

        # Check if magic url contains read instruction
        self.assertIn("ofv", magic_url)

        # Check if uuid in magic url corresponds to returned uuid
        _uuid = response.data["uuid"]
        self.assertIn(_uuid, magic_url)

        # Check if generated token is valid
        token = magic_url.split("/")[-2]
        valid_token = document_token_generator.check_token(self.user, _uuid, token)
        self.assertTrue(valid_token)

        # Check if another user can validate token
        user = UserFactory.create()
        invalid_token = document_token_generator.check_token(user, _uuid, token)
        self.assertFalse(invalid_token)

        # Check if another uuid can validate the token
        _uuid = str(uuid.uuid4())
        invalid_token = document_token_generator.check_token(self.user, _uuid, token)
        self.assertFalse(invalid_token)

    @mock.patch("doc.core.resource.WebDavResource", get_storage_mock())
    def test_magic_url_get(self, m):
        """
        This tests if the magic url finds the document file object and the document.
        """
        self.setUpMock(m)

        # Prepare data
        data = {
            "drc_url": self.test_doc_url,
            "purpose": DocFileTypes.read,
        }
        response = self.client.post(self.list_url, data)
        magic_url = response.data["magic_url"]
        _uuid = response.data["uuid"]

        # Check if magic url points to document
        magic_url_parsed = urlparse(magic_url.split("|")[2])
        response = self.client.get(magic_url_parsed.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
