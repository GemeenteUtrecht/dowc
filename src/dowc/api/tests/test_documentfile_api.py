import uuid
from unittest.mock import patch

import requests_mock
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from dowc.accounts.tests.factories import UserFactory
from dowc.core.constants import DocFileTypes
from dowc.core.models import DocumentFile
from dowc.core.tests.factories import DocumentFileFactory

from .utils import get_url_kwargs


@temp_private_root()
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
            "dowc.core.models.get_document", return_value=document
        )

        # Create fake content
        cls.content = b"some content"
        cls.download_document_content_patcher = patch(
            "dowc.core.models.get_document_content", return_value=cls.content
        )

        # Create a response for update_document call
        cls.update_document_patcher = patch(
            "dowc.core.models.update_document", return_value=document
        )

        # Create random lock data
        cls.lock = uuid.uuid4().hex

        cls.lock_document_patcher = patch(
            "dowc.core.models.lock_document", return_value=cls.lock
        )

        cls.unlock_document_patcher = patch(
            "dowc.core.models.unlock_document", return_value=""
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

        self.lock_document_patcher.start()
        self.addCleanup(self.lock_document_patcher.stop)

        self.unlock_document_patcher.start()
        self.addCleanup(self.unlock_document_patcher.stop)

    def test_create_read_document_file_through_API(self, m):
        """
        Through the API endpoints a documentfile can be created.
        This tests if a POST request on the list_url creates a documentfile with purpose read.
        """

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
        docfile = DocumentFile.objects.get(uuid=docfile_uuid)

        # Check if documentfile object has purpose read
        self.assertTrue(docfile.purpose, DocFileTypes.read)

    def test_delete_document_file_through_API(self, m):
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

    def test_create_write_document_file_through_API(self, m):
        """
        This tests if a POST request on the list_url creates a documentfile with purpose write.
        """

        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
        }

        # Call post on list
        response = self.client.post(self.list_url, data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if purpose is kicked back
        self.assertIn("purpose", response.data)

        # Assert purpose == DocFileTypes.write
        self.assertTrue(response.data["purpose"], DocFileTypes.write)

        # Check if magic_url is kicked back
        self.assertIn("magic_url", response.data)
        magic_url = response.data["magic_url"]

        # Check if magic url contains write instruction
        self.assertIn("ofe", magic_url)

        # Get UUID from URL
        kwargs = get_url_kwargs(magic_url)
        self.assertIn("uuid", kwargs)
        docfile_uuid = kwargs["uuid"]

        # Check created documentfile object
        docfile = DocumentFile.objects.get(uuid=docfile_uuid)

        # Check if documentfile object has purpose write
        self.assertTrue(docfile.purpose, DocFileTypes.write)

    def test_delete_write_document_file_through_API(self, m):
        """
        This tests if a DELETE request on the documentfile-detail url
        deletes a documentfile object write purpose.
        """
        mock_service_oas_get(m, self.DRC_URL, "drc")

        docfile = DocumentFileFactory.create(
            drc_url=self.doc_url, purpose=DocFileTypes.write, user=self.user
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

    def test_return_409_on_duplicate_write_document_file_through_API(self, m):
        """
        This tests if a request for the same write documentfile from the same user
        without the first documentfile being deleted because it was updated
        returns a 409 conflict status.
        """

        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
        }

        # Call post on list
        response = self.client.post(self.list_url, data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if purpose is kicked back
        self.assertIn("purpose", response.data)

        # Assert purpose == DocFileTypes.write
        self.assertTrue(response.data["purpose"], DocFileTypes.write)

        # Check if magic_url is kicked back
        self.assertIn("magic_url", response.data)

        # Call post on list again with same data
        response_duplicate = self.client.post(self.list_url, data)

        # Check response data for 409 response
        self.assertEqual(response_duplicate.status_code, status.HTTP_409_CONFLICT)

    def test_fail_to_create_another_write_documentfile_by_different_user_through_API(
        self, m
    ):
        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
        }

        # Call post on list
        response = self.client.post(self.list_url, data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_user = UserFactory.create()
        self.client.force_authenticate(new_user)

        # Call post on list with different user
        response = self.client.post(self.list_url, data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nonFieldErrors", response.json())

    def test_retrieve_a_documentfile_by_using_filters(self, m):
        mock_service_oas_get(m, self.DRC_URL, "drc")

        DocumentFileFactory.create(
            drc_url=self.doc_url, purpose=DocFileTypes.write, user=self.user
        )
        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
        }

        # Call post on list
        response = self.client.get(self.list_url, params=data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_fail_retrieve_a_documentfile_by_using_filters_and_different_user(self, m):
        mock_service_oas_get(m, self.DRC_URL, "drc")
        DocumentFileFactory.create(
            drc_url=self.doc_url, purpose=DocFileTypes.write, user=self.user
        )
        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
        }

        # Call post on list
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(self.list_url, params=data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
