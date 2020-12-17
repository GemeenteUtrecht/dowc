import base64
import os
import uuid

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from doc.accounts.models import User
from doc.accounts.tests.factories import UserFactory
from doc.api.serializers import DocumentFileSerializer, UserSerializer
from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile
from doc.core.tests.utils import generate_oas_component, mock_service_oas_get

from .utils import AuthMixin

DRC_URL = "https://some.drc.nl/api/v1/"


@requests_mock.Mocker()
class ReviewRequestTests(AuthMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.drc, api_root=DRC_URL)
        cls.list_url = reverse_lazy("documentfile-list")

    @freeze_time("2020-12-17T16:35:00Z")
    def test_create_read_document_file(self, m):
        _uuid = str(uuid.uuid4())

        mock_service_oas_get(m, DRC_URL, "drc")
        test_doc_url = f"{DRC_URL}enkelvoudiginformatieobjecten/{_uuid}"
        test_doc_download_url = f"{test_doc_url}/download"
        doc_data = generate_oas_component("drc", "schemas/EnkelvoudigInformatieObject",)
        doc_data.update(
            {
                "bestandsnaam": "bestandsnaam.docx",
                "inhoud": test_doc_download_url,
                "url": test_doc_url,
            }
        )
        m.get(test_doc_url, json=doc_data)
        m.get(test_doc_download_url, json=["Beetje aan het testen."])
        data = {
            "url": test_doc_url,
            "user": {"username": self.user.username, "email": self.user.email,},
            "purpose": "read",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("uuid", response.data)
        _uuid = response.data["uuid"]
        docfile = DocumentFile.objects.filter(uuid=_uuid)
        self.assertTrue(docfile.exists())
        self.assertEqual(docfile[0].user.username, self.user.username)
        self.assertEqual(docfile[0].user.email, self.user.email)
        self.assertEqual(docfile[0].purpose, "read")
        self.assertEqual(docfile[0].url, test_doc_url)
