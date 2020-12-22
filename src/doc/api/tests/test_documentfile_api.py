import requests_mock
from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase

from doc.api.tests.mixins import AuthMixin
from doc.core.models import DocumentFile
from doc.core.tests.mixins import SetUpMockMixin


@requests_mock.Mocker()
class DocumentFileTests(SetUpMockMixin, AuthMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.list_url = reverse_lazy("documentfile-list")

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
            "user": {"username": self.user.username, "email": self.user.email,},
            "purpose": "read",
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
