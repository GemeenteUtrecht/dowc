import json
import os
import unittest.mock as mock
import uuid

from django.db import transaction
from django.db.utils import IntegrityError

import requests_mock
from privates.test import temp_private_root
from psycopg2.errors import UniqueViolation
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from doc.accounts.tests.factories import UserFactory
from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile
from doc.core.tests.factories import DocumentFileFactory


@requests_mock.Mocker()
class DocumentFileModelTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.DRC_URL = "https://some.drc.nl/api/v1/"
        Service.objects.create(api_type=APITypes.drc, api_root=cls.DRC_URL)
        cls.user = UserFactory.create()

        # Create mock url for drc object
        cls._uuid = str(uuid.uuid4())
        cls.test_doc_url = f"{cls.DRC_URL}enkelvoudiginformatieobjecten/{cls._uuid}"

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def setUpMock(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")

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

    @temp_private_root()
    def test_create_and_delete_read_documentfile(self, m):
        """
        Creating a documentfile with purpose == read gets the document from the DRC.

        This checks:
            1) if the documentfile is created successfully with the factory
            2) if a call is made to get the document
            3) if a call is made to get the document content
            4) if the documentfile is deleted with all associated
            files and folders once force_delete is called.
        """
        self.setUpMock(m)

        # Start of 1
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )
        _uuid = docfile.uuid

        docfiles = DocumentFile.objects.filter(uuid=_uuid)
        self.assertTrue(docfiles.exists())

        self.assertEqual(docfile.drc_url, self.test_doc_url)
        self.assertEqual(docfile.purpose, DocFileTypes.read)
        self.assertEqual(docfile.user.username, self.user.username)
        self.assertEqual(docfile.user.email, self.user.email)

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))
        original_doc_name = docfile.original_document.name
        original_storage = docfile.original_document.storage
        self.assertTrue(original_storage.exists(original_doc_name))

        # Check if document exists at path and with the right content
        with storage.open(docfile.document.name) as open_doc:
            self.assertEqual(open_doc.read(), self.content)

        # Check if filename corresponds to filename on document
        self.assertEqual(docfile.filename, self.bestandsnaam)

        # 2
        self.assertEqual(m.request_history[-2].url, self.test_doc_url)

        # 3
        self.assertEqual(m.request_history[-1].url, self.test_doc_download_url)

        # Delete
        docfile.delete()

        # Check if files exist
        self.assertFalse(storage.exists(doc_name))
        self.assertFalse(original_storage.exists(original_doc_name))

    @temp_private_root()
    @mock.patch("doc.core.models.logger")
    def test_create_update_and_delete_edit_documentfile(self, m, mock_logger):
        """
        Creating a documentfile with purpose == edit locks the document on the
        DRC API.
        Hence, when it needs to be deleted it first needs to be unlocked.

        This checks if:
            1) the documentfile is created successfully with the factory
            2) a call is made to lock the document
            3) lock hash is set
            4) a call is made to get the document
            5) a call is made to get the document content
            6) patch call to DRC API is made when update_drc_document is called
            7) deletion fails when deletion == False
            8) force_delete calls unlock document
            9) the documentfile is deleted with all associated
            files and folders once force_delete is called.
        """
        self.setUpMock(m)
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.edit,
        )
        _uuid = docfile.uuid

        docfiles = DocumentFile.objects.filter(uuid=_uuid)
        # 1
        self.assertTrue(docfiles.exists())
        self.assertEqual(docfile.purpose, DocFileTypes.edit)

        # 2
        self.assertEqual(m.request_history[-3].url, self.test_doc_lock_url)
        self.assertEqual(m.request_history[-3].method, "POST")

        # 3
        self.assertTrue(len(docfile.lock) > 0)

        # 4
        self.assertEqual(m.request_history[-2].url, self.test_doc_url)
        self.assertEqual(m.request_history[-2].method, "GET")

        # 5
        self.assertEqual(m.request_history[-1].url, self.test_doc_download_url)
        self.assertEqual(m.request_history[-1].method, "GET")

        # Start of 6
        # Change file content so that any(changes) returns True
        with docfile.document.storage.open(docfile.document.name, mode="wb") as new_doc:
            new_doc.write(b"some-content")

        # Create mock for call
        m.patch(docfile.drc_url, json=self.doc_data)

        # call
        docfile.update_drc_document()
        self.assertEqual(m.request_history[-1].url, docfile.drc_url)
        self.assertEqual(m.request_history[-1].method, "PATCH")
        # End of 6

        # Start of 7
        docfile.delete()
        self.assertTrue(mock_logger.warning.called)
        mock_logger.warning.assert_called_with(
            "Object: DocumentFile {_uuid} has not been marked for deletion and has locked {drc_url} with lock {lock}.".format(
                _uuid=docfile.uuid, drc_url=docfile.drc_url, lock=docfile.lock
            ),
        )
        # End of 7

        # Start of 8
        # Create mock for call
        test_doc_unlock_url = f"{docfile.drc_url}/unlock"
        m.post(test_doc_unlock_url, json=[], status_code=204)

        # Call
        storage = docfile.document.storage
        name = docfile.document.name
        original_storage = docfile.original_document.storage
        original_name = docfile.original_document.name

        docfile.force_delete()
        self.assertEqual(m.request_history[-1].url, test_doc_unlock_url)
        self.assertEqual(m.request_history[-1].method, "POST")
        # End of 8

        # 9
        # Check if files exist
        self.assertFalse(storage.exists(name))
        self.assertFalse(original_storage.exists(original_name))

    @temp_private_root()
    def test_fail_duplicate_edit_creation(self, m):
        """
        An attempt to save duplicate edit documentfiles should lead to an integrity error
        that can be read from the logger.
        """
        self.setUpMock(m)

        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.edit, user=self.user
        )

        with transaction.atomic():
            DocumentFile.objects.create(
                drc_url=self.test_doc_url,
                purpose=DocFileTypes.edit,
                user=self.user,
            )

        docfiles = DocumentFile.objects.filter(drc_url=self.test_doc_url)
        self.assertEqual(len(docfiles), 1)

    @temp_private_root()
    def test_duplicate_read_creation(self, m):
        """
        An attempt to save duplicate read documentfiles should be successful
        """
        self.setUpMock(m)
        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )
        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )

    @temp_private_root()
    def test_read_and_edit_creation(self, m):
        """
        An attempt to save duplicate documentfiles with only changed purpose should be successful
        """
        self.setUpMock(m)
        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.edit, user=self.user
        )
        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )
