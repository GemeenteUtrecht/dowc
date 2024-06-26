import uuid
from unittest.mock import patch

from django.core import mail
from django.db import transaction
from django.utils.translation import gettext_lazy as _

import requests_mock
from furl import furl
from privates.test import temp_private_root
from rest_framework.exceptions import APIException
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from dowc.accounts.tests.factories import UserFactory
from dowc.core.constants import DOCUMENT_COULD_NOT_BE_UNLOCKED, DocFileTypes
from dowc.core.models import DocumentFile, delete_files
from dowc.core.tests.factories import DocumentFileFactory


@temp_private_root()
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

        # Create mock document data from drc
        cls.doc_data = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.bestandsnaam = "bestandsnaam.docx"
        cls.doc_data.update(
            {
                "bestandsnaam": cls.bestandsnaam,
                "url": cls.test_doc_url,
            }
        )
        cls.document = factory(Document, cls.doc_data)
        cls.get_document_patcher = patch(
            "dowc.core.models.get_document", return_value=cls.document
        )

        # Create fake content
        cls.content = b"some content"
        cls.download_document_content_patcher = patch(
            "dowc.core.models.get_document_content", return_value=cls.content
        )

        cls.get_client_patcher = patch(
            "dowc.core.utils.get_client",
            lambda func: func,
        )

        # Create random lock data
        cls.lock = uuid.uuid4().hex

        cls.lock_document_patcher = patch(
            "dowc.core.models.lock_document", return_value=cls.lock
        )

    def setUp(self):
        self.get_document_patcher.start()
        self.addCleanup(self.get_document_patcher.stop)

        self.download_document_content_patcher.start()
        self.addCleanup(self.download_document_content_patcher.stop)

        self.get_client_patcher.start()
        self.addCleanup(self.get_client_patcher.stop)

        self.lock_document_patcher.start()
        self.addCleanup(self.lock_document_patcher.stop)

    def test_create_read_documentfile(self, m):
        """
        The read documentfile will only have a document property and not an
        original document property as it's not needed.
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )
        _uuid = docfile.uuid

        # Assert object is created
        docfiles = DocumentFile.objects.filter(uuid=_uuid)
        self.assertTrue(docfiles.exists())

        # Assert attributes are correct
        self.assertEqual(docfile.drc_url, self.test_doc_url)
        self.assertEqual(docfile.purpose, DocFileTypes.read)
        self.assertEqual(docfile.user.username, self.user.username)
        self.assertEqual(docfile.user.email, self.user.email)

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Make sure docfile's original_document is empty as it's a read documentfile
        self.assertFalse(docfile.original_document)

        # Check if document exists at path and with the right content
        with storage.open(docfile.document.name) as open_doc:
            self.assertEqual(open_doc.read(), self.content)

        # Check if filename corresponds to filename on document
        self.assertEqual(docfile.filename, self.bestandsnaam)

    def test_delete_files(self, m):
        """
        Tests if files are indeed deleted
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Check if delete_files deletes files
        delete_files(docfile)
        self.assertFalse(storage.exists(doc_name))

    def test_delete_read_documentfile(self, m):
        """
        Tests if the read documentfile with all associated files is deleted
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Make sure docfile's original_document is empty as it's a read documentfile
        self.assertFalse(docfile.original_document)

        # Delete
        docfile.delete()

        # Check if files are deleted
        self.assertFalse(storage.exists(doc_name))

    def test_force_delete_read_documentfile(self, m):
        """
        A force_delete on a read documentfile is the same as a normal deletion request.
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Make sure docfile's original_document is empty as it's a read documentfile
        self.assertFalse(docfile.original_document)

        # Force delete
        docfile.force_delete()

        # Check if files are deleted
        self.assertFalse(storage.exists(doc_name))

    def test_create_write_documentfile(self, m):
        """
        A write documentfile will lock the resource in the DRC.
        Checks if all attributes are assigned appropriately and
        a lock is provided.
        """
        # Create writeable document
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
        )
        _uuid = docfile.uuid

        docfiles = DocumentFile.objects.filter(uuid=_uuid)

        # Assert it exists with write purpose
        self.assertTrue(docfiles.exists())
        self.assertEqual(docfile.purpose, DocFileTypes.write)

        # Assert the document is locked
        self.assertEqual(docfile.lock, self.lock)

        # Assert attributes are correct
        self.assertEqual(docfile.drc_url, self.test_doc_url)
        self.assertEqual(docfile.user.username, self.user.username)
        self.assertEqual(docfile.user.email, self.user.email)

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))
        original_doc_name = docfile.original_document.name
        original_storage = docfile.original_document.storage
        self.assertTrue(original_storage.exists(original_doc_name))

    def test_update_content_and_size_write_documentfile(self, m):
        """
        A content change should trigger the update_document request
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
        )

        # Change file content so that any(changes) returns True
        with docfile.document.storage.open(docfile.document.name, mode="wb") as new_doc:
            new_doc.write(b"some-content")

        # call update_drc_document
        doc = docfile.update_drc_document()
        self.assertTrue(type(doc) is dict)

    def test_update_name_write_documentfile(self, m):
        """
        A name change should trigger the update_document request
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
        )

        # Change file name so that any(changes) returns True
        docfile.changed_name = True

        # call update_drc_document
        doc = docfile.update_drc_document()
        self.assertTrue(type(doc) is dict)

    def test_update_write_documentfile_user_without_get_full_name(self, m):
        """
        A name change should trigger the update_document request
        """
        user = UserFactory(first_name="", last_name="", username="some-user")
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.write, user=user
        )

        # Change file name so that any(changes) returns True
        docfile.changed_name = True

        # call update_drc_document
        doc = docfile.update_drc_document()
        self.assertTrue(type(doc) is dict)
        self.assertEqual(doc["auteur"], "some-user")

    def test_update_name_write_documentfile_with_get_full_name(self, m):
        """
        A name change should trigger the update_document request
        """
        user = UserFactory(first_name="First", last_name="Last", username="some-user")
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.write, user=user
        )

        # Change file name so that any(changes) returns True
        docfile.changed_name = True

        # call update_drc_document
        doc = docfile.update_drc_document()
        self.assertTrue(type(doc) is dict)
        self.assertEqual(doc["auteur"], "First Last")

    def test_no_change_write_documentfile(self, m):
        """
        No changes made to the original document so update_document shouldn't trigger
        and update_drc_document returns None.
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
        )

        # call update_drc_document
        doc = docfile.update_drc_document()
        self.assertIsNone(doc)

    @patch("dowc.core.models.logger")
    def test_fail_delete_write_documentfile(self, m, mock_logger):
        """
        Trying to delete a write documentfile that is still locked and unsafe for deletion
        should trigger a warning in logger and ignores the deletion request.

        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            unversioned_url=furl(self.test_doc_url).remove(args=True).url,
        )

        # Call delete...
        docfile.delete()
        # ... and assert a warning has been given that said it failed.
        self.assertTrue(mock_logger.warning.called)
        mock_logger.warning.assert_called_with(
            "Object: DocumentFile {_uuid} has not been marked for deletion and has locked {url} with lock {lock}.".format(
                _uuid=docfile.uuid, url=docfile.unversioned_url, lock=docfile.lock
            ),
        )

    def test_force_delete_write_documentfile(self, m):
        """
        A force_delete request on a write documentfile should first unlock the document
        in the DRC. Continue the deletion if that's successful.

        """

        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
        )

        # Make sure files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))
        original_doc_name = docfile.original_document.name
        original_storage = docfile.original_document.storage
        self.assertTrue(original_storage.exists(original_doc_name))

        with patch("dowc.core.models.unlock_document", return_value=(None, True)):
            docfile.force_delete()

        # Make sure files are deleted
        self.assertFalse(storage.exists(doc_name))
        self.assertFalse(original_storage.exists(original_doc_name))

        # Check email was sent
        email = mail.outbox[0]

        self.assertEqual(
            email.body,
            "Beste {name},\n\n".format(name=self.user.username)
            + "Uw openstaande document {filename} is gesloten en de wijzigingen zijn doorgevoerd.\n".format(
                filename=self.document.bestandsnaam
            )
            + "U kunt uw document vinden als u de volgende link volgt: {info_url}\n\n".format(
                info_url=docfile.info_url
            )
            + "Met vriendelijke groeten,\n\nFunctioneel Beheer Gemeente Utrecht",
        )
        self.assertEqual(
            email.subject,
            _("We saved your unfinished document: {filename}").format(
                filename=self.document.bestandsnaam
            ),
        )
        self.assertEqual(email.to, [self.user.email])

    def test_fail_force_delete_write_documentfile(self, m):
        """
        Make sure that if unlock_document raises an HTTPError documentfile will not be deleted.

        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
        )

        # Make sure files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))
        original_doc_name = docfile.original_document.name
        original_storage = docfile.original_document.storage
        self.assertTrue(original_storage.exists(original_doc_name))

        with patch("dowc.core.models.unlock_document", return_value=(None, False)):
            docfile.force_delete()

        # Make sure files still exist
        self.assertTrue(storage.exists(doc_name))
        self.assertTrue(original_storage.exists(original_doc_name))
        docfile.refresh_from_db()
        self.assertTrue(docfile.error)
        self.assertEqual(docfile.error_msg, DOCUMENT_COULD_NOT_BE_UNLOCKED)

    def test_fail_duplicate_write_creation(self, m):
        """
        An attempt to save duplicate write documentfiles should lead to an APIException

        """

        DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
            unversioned_url=furl(self.test_doc_url).remove(args=True).url,
        )

        with self.assertRaises(APIException):
            with transaction.atomic():
                DocumentFile.objects.create(
                    drc_url=self.test_doc_url,
                    purpose=DocFileTypes.write,
                    user=self.user,
                    unversioned_url=furl(self.test_doc_url).remove(args=True).url,
                )

        docfiles = DocumentFile.objects.filter(drc_url=self.test_doc_url)
        self.assertEqual(len(docfiles), 1)

    def test_duplicate_read_creation(self, m):
        """
        An attempt to save duplicate read documentfiles should be successful.
        """

        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )
        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )

    def test_read_and_edit_creation(self, m):
        """
        An attempt to save duplicate documentfiles with different purposes should be successful.
        """

        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.write, user=self.user
        )
        DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )
