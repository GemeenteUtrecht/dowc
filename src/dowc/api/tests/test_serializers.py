import tempfile
import uuid
from unittest.mock import patch
from urllib.parse import urlparse

from django.conf import settings
from django.test import override_settings
from django.test.client import RequestFactory

from rest_framework import status
from rest_framework.reverse import reverse_lazy
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from dowc.accounts.tests.factories import UserFactory
from dowc.api.serializers import DocumentFileSerializer
from dowc.core.constants import DocFileTypes
from dowc.core.models import DocumentFile
from dowc.core.resource import WebDavResource
from dowc.core.tests.factories import DocumentFileFactory
from dowc.core.tokens import document_token_generator

from .utils import get_url_kwargs

tmpdir = tempfile.mkdtemp()

# Mock storage for test_magic_url_get
@override_settings(PRIVATE_MEDIA_ROOT=tmpdir)
def get_storage_mock():
    storage_mock = WebDavResource
    storage_mock.root = settings.PRIVATE_MEDIA_ROOT
    storage_mock.exists = True
    return storage_mock


class DocumentFileSerializerTests(APITestCase):
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

    @override_settings(PRIVATE_MEDIA_ROOT=tmpdir)
    def test_magic_url_parameters(self):
        """
        This tests the creation of the magic url token(s).
        """

        docfile = DocumentFileFactory.create(
            drc_url=self.doc_url, purpose=DocFileTypes.read, user=self.user
        )

        result = DocumentFileSerializer(docfile)
        result.context["request"] = RequestFactory().post(self.list_url)
        # Assert presence of magic_url in result.data
        self.assertIn("magic_url", result.data)
        magic_url = result.data["magic_url"]

        # Get information from magic_url
        kwargs = get_url_kwargs(magic_url)

        # Get UUID from URL ...
        self.assertIn("uuid", kwargs)
        docfile_uuid = kwargs["uuid"]

        # ... and check if there is a documentfile with that uuid
        self.assertTrue(DocumentFile.objects.filter(uuid=docfile_uuid).exists())

        # Get purpose from url
        self.assertIn("purpose", kwargs)
        self.assertEqual(kwargs["purpose"], docfile.purpose)

        # Get path from url
        self.assertIn("path", kwargs)
        self.assertEqual(kwargs["path"], docfile.document.name)

        # Get token from url
        self.assertIn("token", kwargs)
        token = kwargs["token"]

        # Check if token is valid
        valid_token = document_token_generator.check_token(
            self.user, kwargs["uuid"], token
        )
        self.assertTrue(valid_token)

        # Check if another user can validate token
        user = UserFactory.create()
        invalid_token = document_token_generator.check_token(
            user, kwargs["uuid"], token
        )
        self.assertFalse(invalid_token)

        # Check if another uuid can validate the token
        _uuid = str(uuid.uuid4())
        invalid_token = document_token_generator.check_token(
            self.user, uuid.uuid4(), token
        )
        self.assertFalse(invalid_token)

    @patch("dowc.core.resource.WebDavResource", get_storage_mock())
    @override_settings(PRIVATE_MEDIA_ROOT=tmpdir)
    def test_magic_url_get(self):
        """
        This tests if the magic url finds the document file object and the document.
        """

        docfile = DocumentFileFactory.create(
            drc_url=self.doc_url, purpose=DocFileTypes.read, user=self.user
        )

        result = DocumentFileSerializer(docfile)
        result.context["request"] = RequestFactory().post(self.list_url)

        # Assert presence of magic_url in result.data
        self.assertIn("magic_url", result.data)
        magic_url = result.data["magic_url"]

        # Check if magic url points to document
        magic_url_parsed = urlparse(magic_url.split("|u|")[-1])
        response = self.client.get(magic_url_parsed.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
