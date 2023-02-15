import uuid
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from privates.test import temp_private_root
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from dowc.accounts.tests.factories import UserFactory
from dowc.core.constants import (
    DOCUMENT_COULD_NOT_BE_UNLOCKED,
    DOCUMENT_COULD_NOT_BE_UPDATED,
    DocFileTypes,
)
from dowc.core.models import DocumentFile
from dowc.core.tests.factories import DocumentFileFactory


@temp_private_root()
class DocumentFileManagerTests(TestCase):
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

    def test_delete_read_documentfiles(self):
        """
        Tests if files belonging to read_documentfiles are deleted
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Call manager delete
        deleted, rows = DocumentFile.objects.delete()
        self.assertEqual(deleted, 1)
        self.assertFalse(DocumentFile.objects.all().exists())
        self.assertFalse(storage.exists(doc_name))

    def test_delete_read_documentfiles_and_safe_for_deletion(self):
        """
        Tests if files and data belonging to safe_for_deletion and read documentfiles are deleted
        """
        read_docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.read,
            user=self.user,
        )
        write_docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            safe_for_deletion=True,
            user=self.user,
        )

        # Check if files exist
        read_storage = read_docfile.document.storage
        read_doc_name = read_docfile.document.name
        self.assertTrue(read_storage.exists(read_doc_name))
        write_storage = write_docfile.document.storage
        write_doc_name = write_docfile.document.name
        self.assertTrue(write_storage.exists(write_doc_name))

        # Call manager delete
        deleted, rows = DocumentFile.objects.delete()
        self.assertEqual(deleted, 2)
        self.assertFalse(DocumentFile.objects.all().exists())
        self.assertFalse(read_storage.exists(read_doc_name))
        self.assertFalse(write_storage.exists(write_doc_name))

    def test_delete_read_documentfiles_and_not_unsafe_for_deletion(self):
        """
        Tests if files and data belonging to safe_for_deletion are not and read documentfiles are deleted
        """
        read_docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.read,
            user=self.user,
        )
        write_docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            safe_for_deletion=False,
            user=self.user,
        )

        # Check if files exist
        read_storage = read_docfile.document.storage
        read_doc_name = read_docfile.document.name
        self.assertTrue(read_storage.exists(read_doc_name))
        write_storage = write_docfile.document.storage
        write_doc_name = write_docfile.document.name
        self.assertTrue(write_storage.exists(write_doc_name))

        # Call manager delete
        deleted, rows = DocumentFile.objects.delete()
        self.assertEqual(deleted, 1)
        self.assertEqual(DocumentFile.objects.count(), 1)
        self.assertFalse(read_storage.exists(read_doc_name))
        self.assertTrue(write_storage.exists(write_doc_name))

    def test_delete_read_documentfiles_and_not_errored(self):
        """
        Tests if files and data belonging to errored are not and read documentfiles are deleted
        """
        read_docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.read,
            user=self.user,
        )
        write_docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            safe_for_deletion=True,
            user=self.user,
            error=True,
        )

        # Check if files exist
        read_storage = read_docfile.document.storage
        read_doc_name = read_docfile.document.name
        self.assertTrue(read_storage.exists(read_doc_name))
        write_storage = write_docfile.document.storage
        write_doc_name = write_docfile.document.name
        self.assertTrue(write_storage.exists(write_doc_name))

        # Call manager delete
        deleted, rows = DocumentFile.objects.delete()
        self.assertEqual(deleted, 1)
        self.assertEqual(DocumentFile.objects.count(), 1)
        self.assertFalse(read_storage.exists(read_doc_name))
        self.assertTrue(write_storage.exists(write_doc_name))

    def test_delete_write_documentfiles(self):
        """
        Tests if files belonging to write_documentfiles are deleted
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
            safe_for_deletion=True,
            error=False,
            emailed=False,
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Call manager delete
        deleted, rows = DocumentFile.objects.delete()
        self.assertEqual(deleted, 1)
        self.assertFalse(DocumentFile.objects.all().exists())
        self.assertFalse(storage.exists(doc_name))

    def test_force_delete_read_documentfiles(self):
        """
        Tests if files belonging to write_documentfiles are force deleted
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.read,
            user=self.user,
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        deleted = DocumentFile.objects.force_delete()
        self.assertEqual(deleted, 1)
        self.assertFalse(DocumentFile.objects.all().exists())
        self.assertFalse(storage.exists(doc_name))

    def test_force_delete_write_documentfiles(self):
        """
        Tests if files belonging to write_documentfiles are force deleted
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
            safe_for_deletion=False,
            error=False,
            emailed=False,
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Call manager delete
        with patch(
            "dowc.core.managers.update_document", return_value=(self.document, True)
        ):
            with patch(
                "dowc.core.managers.unlock_document", return_value=(self.document, True)
            ):
                deleted = DocumentFile.objects.force_delete()
        self.assertEqual(deleted, 1)
        self.assertFalse(DocumentFile.objects.all().exists())
        self.assertFalse(storage.exists(doc_name))

        # Check if receiver signal is received and an email is sent.
        self.assertTrue(len(mail.outbox) > 0)

    def test_force_delete_write_documentfiles_cannot_update(self):
        """
        Tests if files belonging to write_documentfiles are force deleted
        if they cannot be updated on the DRC.
        """
        docfile = DocumentFileFactory.create(
            unversioned_url=self.document.url,
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
            safe_for_deletion=False,
            error=False,
            emailed=False,
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Call manager delete
        with patch(
            "dowc.core.models.DocumentFile.update_drc_document",
            return_value=True,
        ):
            with patch(
                "dowc.core.managers.update_document",
                return_value=(self.document.url, False),
            ):
                deleted = DocumentFile.objects.force_delete()
        self.assertEqual(deleted, 0)
        self.assertTrue(DocumentFile.objects.all().exists())
        self.assertTrue(DocumentFile.objects.get().error)
        self.assertEqual(
            DocumentFile.objects.get().error_msg, DOCUMENT_COULD_NOT_BE_UPDATED
        )
        self.assertTrue(storage.exists(doc_name))

    def test_force_delete_write_documentfiles_cannot_unlock(self):
        """
        Tests if files belonging to write_documentfiles are force deleted
        if they cannot be unlocked on the DRC.
        """
        docfile = DocumentFileFactory.create(
            unversioned_url=self.document.url,
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
            safe_for_deletion=False,
            error=False,
            emailed=False,
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Call manager delete
        with patch(
            "dowc.core.managers.unlock_document",
            return_value=(self.document.url, False),
        ):
            deleted = DocumentFile.objects.force_delete()
        self.assertEqual(deleted, 0)
        self.assertTrue(DocumentFile.objects.all().exists())
        self.assertTrue(DocumentFile.objects.get().error)
        self.assertEqual(
            DocumentFile.objects.get().error_msg, DOCUMENT_COULD_NOT_BE_UNLOCKED
        )
        self.assertTrue(storage.exists(doc_name))

    def test_force_delete_read_and_write_documentfiles(self):
        """
        Tests if files belonging to write_documentfiles are force deleted
        """
        docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
            safe_for_deletion=False,
            error=False,
            emailed=False,
        )

        # Check if files exist
        storage = docfile.document.storage
        doc_name = docfile.document.name
        self.assertTrue(storage.exists(doc_name))

        # Call manager delete
        with patch(
            "dowc.core.managers.update_document", return_value=(self.document, True)
        ):
            with patch(
                "dowc.core.managers.unlock_document", return_value=(self.document, True)
            ):
                deleted = DocumentFile.objects.force_delete()
        self.assertEqual(deleted, 1)
        self.assertFalse(DocumentFile.objects.all().exists())
        self.assertFalse(storage.exists(doc_name))

        # Check if receiver signal is received and an email is sent.
        self.assertTrue(len(mail.outbox) > 0)
