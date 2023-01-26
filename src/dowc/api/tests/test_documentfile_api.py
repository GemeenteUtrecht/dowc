import os
import uuid
from io import BytesIO
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


def set_docfile_content(docfile: DocumentFile, content: bytes):
    filename = os.path.basename(docfile.document.name)
    # delete old file so we can re-use the name
    docfile.document.storage.delete(filename)
    docfile.document.save(filename, BytesIO(content))


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

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        cls.doc_url = f"{cls.DRC_URL}enkelvoudiginformatieobjecten/{_uuid}"

        # Create mock document data from drc
        bestandsnaam = "some-filename.docx"
        cls.doc_data = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=cls.doc_url,
            bestandsnaam=bestandsnaam,
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

        # Create random lock data
        cls.lock = uuid.uuid4().hex

        cls.lock_document_patcher = patch(
            "dowc.core.models.lock_document", return_value=cls.lock
        )

        cls.unlock_document_patcher = patch(
            "dowc.core.models.unlock_document",
            return_value=factory(
                Document,
                {**cls.doc_data, "versie": 42},
            ),
        )

        cls.update_document_patcher = patch(
            "dowc.api.viewsets.update_document",
            return_value=cls.doc_data,
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

        self.get_document_patcher.start()
        self.addCleanup(self.get_document_patcher.stop)

        self.download_document_content_patcher.start()
        self.addCleanup(self.download_document_content_patcher.stop)

        self.lock_document_patcher.start()
        self.addCleanup(self.lock_document_patcher.stop)

        self.mock_unlock = self.unlock_document_patcher.start()
        self.addCleanup(self.unlock_document_patcher.stop)

    def test_create_read_document_file_through_API(self, m):
        """
        Through the API endpoints a documentfile can be created.
        This tests if a POST request on the list_url creates a documentfile with purpose read.
        """

        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.read,
            "info_url": "http://www.some-referer-url.com/",
        }

        # Call post on list
        response = self.client.post(self.list_url, data)

        # Check response status
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

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if docfile exists
        self.assertFalse(DocumentFile.objects.filter(uuid=_uuid).exists())

    def test_create_write_document_file_through_API(self, m):
        """
        This tests if a POST request on the list_url creates a documentfile with purpose write.
        """

        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
            "info_url": "http://www.some-referer-url.com/",
        }

        # Call post on list
        response = self.client.post(self.list_url, data)

        # Check response status
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

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if docfile exists
        self.assertFalse(DocumentFile.objects.filter(uuid=_uuid).exists())

    def test_changed_document_persisted_to_documents_api(self, m):
        mock_service_oas_get(m, self.DRC_URL, "drc")
        docfile = DocumentFileFactory.create(
            drc_url=self.doc_url, purpose=DocFileTypes.write, user=self.user
        )
        delete_url = reverse("documentfile-detail", kwargs={"uuid": docfile.uuid})
        # 'edit' the document
        set_docfile_content(docfile, b"other content")

        with self.update_document_patcher as mock_update:
            response = self.client.delete(delete_url)

        mock_update.assert_called_once()
        self.mock_unlock.assert_called_once()
        self.assertEqual(
            response.json()["versionedUrl"], f"{self.doc_data['url']}?versie=42"
        )

    def test_return_409_on_duplicate_write_document_file_through_API(self, m):
        """
        This tests if a request for the same write documentfile from the same user
        without the first documentfile being deleted because it was updated
        returns a 409 conflict status.
        """

        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
            "info_url": "http://www.some-referer-url.com/",
        }

        # Call post on list
        response = self.client.post(self.list_url, data)

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if purpose is kicked back
        self.assertIn("purpose", response.data)

        # Assert purpose == DocFileTypes.write
        self.assertTrue(response.data["purpose"], DocFileTypes.write)

        # Check if magic_url is kicked back
        self.assertIn("magic_url", response.data)

        # Call post on list again with same data
        response_duplicate = self.client.post(self.list_url, data)

        # Check response status for 409 response
        self.assertEqual(response_duplicate.status_code, status.HTTP_409_CONFLICT)

    def test_fail_to_create_another_write_documentfile_by_different_user_through_API(
        self, m
    ):
        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
            "info_url": "http://www.some-referer-url.com/",
        }

        # Call post on list
        response = self.client.post(self.list_url, data)

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_user = UserFactory.create()
        self.client.force_authenticate(new_user)

        # Call post on list with different user
        response = self.client.post(self.list_url, data)

        # Check response status
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

        # Call get on list
        response = self.client.get(self.list_url, data=data)

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_multiple_documentfile_with_same_info_url(self, m):
        mock_service_oas_get(m, self.DRC_URL, "drc")

        # Two documentfiles for user with purpose to write
        DocumentFileFactory.create_batch(
            2,
            info_url="http://some-source-url.com/",
            purpose=DocFileTypes.write,
            user=self.user,
        )
        # One documentfile for user with different source url (should not be retrieved)
        DocumentFileFactory.create(
            info_url="http://some-other-source-url.com/",
            purpose=DocFileTypes.write,
            user=self.user,
        )
        # One documentfile for user with purpose to read (should not be retrieved)
        DocumentFileFactory.create(
            info_url="http://some-source-url.com/",
            purpose=DocFileTypes.read,
            user=self.user,
        )
        user2 = UserFactory.create()
        # One documentfile from same info_url and purpose to write but different user (should not be retrieved)
        DocumentFileFactory.create(
            info_url="http://some-source-url.com/",
            purpose=DocFileTypes.write,
            user=user2,
        )

        # Retrieve documentfiles with this data
        data = {
            "info_url": "http://some-source-url.com/",
            "purpose": DocFileTypes.write,
        }

        # Call get on list
        response = self.client.get(self.list_url, data=data)

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        # Expecting 2 documentfiles
        self.assertEqual(len(results), 2)

    def test_fail_retrieve_a_documentfile_by_using_filters_and_different_user(self, m):
        mock_service_oas_get(m, self.DRC_URL, "drc")
        DocumentFileFactory.create(
            drc_url=self.doc_url, purpose=DocFileTypes.write, user=self.user
        )
        data = {
            "drc_url": self.doc_url,
            "purpose": DocFileTypes.write,
        }

        # Call get on list
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(self.list_url, data=data)

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_documentfiles_for_zaak(self, m):
        mock_service_oas_get(m, self.DRC_URL, "drc")

        # Two documentfiles for user with purpose to write
        DocumentFileFactory.create_batch(
            2,
            zaak="http://some-source-url.com/",
            purpose=DocFileTypes.write,
        )

        # Retrieve documentfiles with this data
        data = {
            "zaak": "http://some-source-url.com/",
        }

        # Call get on list
        response = self.client.get(reverse_lazy("documentfile-count"), data=data)

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()

        # Expecting 2 documentfiles
        self.assertEqual(results["count"], 2)
