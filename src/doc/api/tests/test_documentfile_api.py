import tempfile
import uuid
from unittest.mock import patch
from urllib.parse import urlparse

from django.test import override_settings

import requests_mock
from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from doc.accounts.tests.factories import UserFactory
from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile
from doc.core.tests.factories import DocumentFileFactory

from .utils import get_url_kwargs

tmpdir = tempfile.mkdtemp()


@override_settings(PRIVATE_MEDIA_ROOT=tmpdir)
@requests_mock.Mocker()
class DocumentFileAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.DRC_URL = "https://some.drc.nl/api/v1/"
        Service.objects.create(api_type=APITypes.drc, api_root=cls.DRC_URL)
        cls.list_url = reverse_lazy("documentfile-list")
        cls.user = UserFactory.create()

        # Create mock document data from drc
        cls.doc_data = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )

        bestandsnaam = "some-filename.docx"
        cls.doc_data.update(
            {
                "bestandsnaam": bestandsnaam,
            }
        )

        document = factory(Document, cls.doc_data)
        cls.get_document_patcher = patch(
            "doc.core.models.get_document", return_value=document
        )

        # Create fake content
        cls.content = b"some content"
        cls.download_document_content_patcher = patch(
            "doc.core.models.get_document_content", return_value=cls.content
        )

        # Create a response for update_document call
        cls.update_document_patcher = patch(
            "doc.core.models.update_document", return_value=document
        )

        cls.get_client_patcher = patch(
            "doc.core.utils.get_client",
            lambda func: func,
        )

        # Create random lock data
        cls.lock = uuid.uuid4().hex

        cls.lock_document_patcher = patch(
            "doc.core.models.lock_document", return_value=cls.lock
        )

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        cls.doc_url = f"{cls.DRC_URL}enkelvoudiginformatieobjecten/{_uuid}"

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

        self.get_document_patcher.start()
        self.addCleanup(self.get_document_patcher.stop)

        self.download_document_content_patcher.start()
        self.addCleanup(self.download_document_content_patcher.stop)

        self.get_client_patcher.start()
        self.addCleanup(self.get_client_patcher.stop)

        self.lock_document_patcher.start()
        self.addCleanup(self.lock_document_patcher.stop)

    def test_create_read_document_file_through_API(self, m):
        """
        Through the API endpoints documentfile can be created.
        This tests if a POST request on the list_url creates a documentfile.
        """

        # Prepare data for call 1
        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.read,
        }

        # Call post on list
        response = self.client.post(self.list_url, data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if purpose is kicked back
        self.assertIn("purpose", response.data)

        # Assert purpose == DocFileTypes.read
        self.assertTrue(response.data["purpose"], DocFileTypes.read)

        # Check if magic_url is kicked back
        self.assertIn("magic_url", response.data)
        magic_url = response.data["magic_url"]

        # Check if magic url contains read instruction
        self.assertIn("ofv", magic_url)

        # Get UUID from URL
        kwargs = get_url_kwargs(magic_url)
        self.assertIn("uuid", kwargs)
        docfile_uuid = kwargs["uuid"]

        # Check created documentfile object
        docfile = DocumentFile.objects.filter(uuid=docfile_uuid)
        self.assertTrue(docfile.exists())

    def test_delete_document_file_through_API(self, m):
        """
        Through the API endpoints documentfile can be created.
        This tests if a DELETE request on the documentfile-detail url deletes a documentfile.
        """

        docfile = DocumentFileFactory.create(
            drc_url=self.doc_url, purpose=DocFileTypes.read, user=self.user
        )
        _uuid = docfile.uuid

        # Get delete url
        delete_url = reverse("documentfile-detail", kwargs={"uuid": _uuid})

        # Call delete
        response = self.client.delete(delete_url)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check if docfile exists
        self.assertFalse(DocumentFile.objects.filter(uuid=_uuid).exists())
