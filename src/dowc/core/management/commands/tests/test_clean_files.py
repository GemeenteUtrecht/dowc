import uuid
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from privates.test import temp_private_root
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from dowc.accounts.tests.factories import UserFactory
from dowc.core.constants import DocFileTypes
from dowc.core.models import DocumentFile
from dowc.core.tests.factories import DocumentFileFactory


class SendEmailTests(TestCase):
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

        # Create a response for update_document call
        cls.update_document_patcher = patch(
            "dowc.core.models.update_document", return_value=cls.document
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

    @temp_private_root()
    def test_clean_document_files(self):
        read_docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url, purpose=DocFileTypes.read, user=self.user
        )
        write_docfile = DocumentFileFactory.create(
            drc_url=self.test_doc_url,
            purpose=DocFileTypes.write,
            user=self.user,
            info_url="http://some-referer-url.com/",
        )

        # Assert number of documentfile objects
        number_of_documentfiles = DocumentFile.objects.all().count()
        self.assertEqual(number_of_documentfiles, 2)

        # Check if read document files exist
        read_storage = read_docfile.document.storage
        read_doc_name = read_docfile.document.name
        self.assertTrue(read_storage.exists(read_doc_name))

        # Check if write documentfile files exist
        write_storage = write_docfile.document.storage
        write_doc_name = write_docfile.document.name
        self.assertTrue(write_storage.exists(write_doc_name))

        with patch("dowc.core.managers.unlock_document", return_value=self.document):
            call_command("clean_files")

        # Assert number of documents is zero
        number_of_documentfiles = DocumentFile.objects.all().count()
        self.assertEqual(number_of_documentfiles, 0)

        # Check files are destroyed
        self.assertFalse(read_storage.exists(read_doc_name))
        self.assertFalse(write_storage.exists(write_doc_name))

        # Check email was sent
        email = mail.outbox[0]
        self.assertEqual(
            email.body,
            "Beste {name},\n\n".format(name=self.user.username)
            + "Uw openstaande document {filename} is gesloten en de wijzigingen zijn doorgevoerd.\n".format(
                filename=self.document.bestandsnaam
            )
            + "U kunt uw document vinden als u de volgende link volgt: {info_url}\n\n".format(
                info_url="http://some-referer-url.com/"
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
