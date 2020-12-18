import base64
import json
import os
import shutil
import uuid

import requests
import requests_mock
from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase
from zds_client import client as zds_client
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
class DocumentFileTests(AuthMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.drc, api_root=DRC_URL)
        cls.list_url = reverse_lazy("documentfile-list")

    def delete_folders(self, docfile):
        shutil.rmtree(os.path.dirname(docfile.document.path))
        shutil.rmtree(os.path.dirname(docfile.original_document.path))

    def test_create_read_document_file(self, m, delete=True):
        """
        This calls:
        1) doc_client.post(data)
            1.1) drc_client.get(doc_data) 
            1.2) drc_client.get(dowload_doc_content)
        """

        # Mock drc_client service
        mock_service_oas_get(m, DRC_URL, "drc")

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        test_doc_url = f"{DRC_URL}enkelvoudiginformatieobjecten/{_uuid}"

        # Create mock url for drc document content download
        test_doc_download_url = f"{test_doc_url}/download"

        # Create mock document data from drc
        doc_data = generate_oas_component("drc", "schemas/EnkelvoudigInformatieObject",)
        bestandsnaam = "bestandsnaam.docx"
        doc_data.update(
            {
                "bestandsnaam": bestandsnaam,
                "inhoud": test_doc_download_url,
                "url": test_doc_url,
            }
        )

        # Create mock call 1.1
        m.get(test_doc_url, json=doc_data)

        # Create fake content
        content = b"Beetje aan het testen.".decode("utf-8")

        # Create mock call 1.2
        m.get(test_doc_download_url, json=content)

        # Prepare data for call 1
        data = {
            "drc_url": test_doc_url,
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
        self.assertEqual(docfile[0].user.username, self.user.username)
        self.assertEqual(docfile[0].user.email, self.user.email)
        self.assertEqual(docfile[0].purpose, "read")
        self.assertEqual(docfile[0].drc_url, test_doc_url)

        # Check if document exists at path and with the right content
        with open(docfile[0].document.path) as open_doc:
            self.assertEqual(open_doc.read(), json.dumps(content))

        # Check if filename corresponds to filename on document
        saved_filename = os.path.basename(docfile[0].document.path)
        self.assertEqual(saved_filename, bestandsnaam)

        # Destroy test folders
        if delete:
            self.delete_folders(docfile[0])
        else:
            return docfile[0]

    def test_destroy_read_document_file(self, m):
        """
        This calls test_create_read_document to make a temp docfile
        and then destroys it by calling client.delete.

        It checks if the created folders and files get deleted
        and if the object is deleted.

        Order of events:
            1) client.delete(link_to_docfile)
                1.1) doc.file.purpose = read
                1.2) Unlock document
                1.3) Delete files and created folders   
        """

        # Create test docfile with read purpose
        docfile = self.test_create_read_document_file(delete=False)
        _uuid = docfile.uuid

        # Get filepaths to original document
        fp_to_protected = docfile.document.path
        fp_to_original = docfile.original_document.path

        # Check if files exist
        self.assertTrue(os.path.exists(fp_to_original))
        self.assertTrue(os.path.exists(fp_to_protected))

        # Check if folders exist
        dir_original = os.path.dirname(fp_to_original)
        dir_protected = os.path.dirname(fp_to_protected)
        self.assertTrue(os.path.exists(dir_original))
        self.assertTrue(os.path.exists(dir_protected))

        # Get delete url
        delete_url = reverse("documentfile-detail", kwargs={"uuid": _uuid})

        # Call delete
        response = self.client.delete(delete_url)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check if docfile exists
        self.assertFalse(DocumentFile.objects.filter(uuid=_uuid).exists())

        # Check if files exist
        self.assertFalse(os.path.exists(fp_to_original))
        self.assertFalse(os.path.exists(fp_to_protected))

        # Check if folders exist
        self.assertFalse(os.path.exists(dir_original))
        self.assertFalse(os.path.exists(dir_protected))

    def test_create_edit_document_file(self, m, delete=True):
        """
        This calls:
        1) doc_client.post(data)
            1.1) drc_client.post(lock)
            1.2) drc_client.get(doc_data) 
            1.3) drc_client.get(dowload_doc_content)
        """
        # Mock drc_client service
        mock_service_oas_get(m, DRC_URL, "drc")

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        test_doc_url = f"{DRC_URL}enkelvoudiginformatieobjecten/{_uuid}"

        # Create mock url for locking of drc object
        test_doc_lock_url = f"{test_doc_url}/lock"

        # Create random lock data
        lock = uuid.uuid4().hex

        # Create mock 1.1
        m.post(test_doc_lock_url, json={"lock": lock})

        # Create mock url for drc document content download
        test_doc_download_url = f"{test_doc_url}/download"

        # Create document data
        doc_data = generate_oas_component("drc", "schemas/EnkelvoudigInformatieObject",)
        bestandsnaam = "bestandsnaam.docx"
        doc_data.update(
            {
                "bestandsnaam": bestandsnaam,
                "inhoud": test_doc_download_url,
                "url": test_doc_url,
                "locked": True,
                "lock": lock,
            }
        )

        # Mock call 1.2, document is locked before this point by call 1.1
        m.get(test_doc_url, json=doc_data)

        # Create fake content
        content = b"Beetje aan het testen.".decode("utf-8")

        # Mock call 1.3
        m.get(test_doc_download_url, json=content)
        data = {
            "drc_url": test_doc_url,
            "user": {"username": self.user.username, "email": self.user.email,},
            "purpose": "edit",
        }

        # Call 1
        response = self.client.post(self.list_url, data)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("uuid", response.data)

        # Assert model is created correctly through API
        _uuid = response.data["uuid"]
        docfile = DocumentFile.objects.filter(uuid=_uuid)
        self.assertTrue(docfile.exists())
        self.assertEqual(docfile[0].user.username, self.user.username)
        self.assertEqual(docfile[0].user.email, self.user.email)
        self.assertEqual(docfile[0].purpose, "edit")
        self.assertEqual(docfile[0].drc_url, test_doc_url)

        # Check if document is created at path
        with open(docfile[0].document.path) as open_doc:
            self.assertEqual(open_doc.read(), json.dumps(content))

        # Check if filename corresponds to filename on drc document
        saved_filename = os.path.basename(docfile[0].document.path)
        self.assertEqual(saved_filename, bestandsnaam)

        if delete:
            self.delete_folders(docfile[0])
        else:
            return doc_data, docfile[0]

    def test_destroy_edit_document_file(self, m):
        """
        This calls test_create_edit_document to make a temp docfile
        and then destroys it by calling client.delete.

        Because the document is edited this will call a number of functions 
        in the viewset.perform_destroy.

        Order of events:
            1) client.delete(link_to_docfile)
                1.1) doc.file.purpose = "edit"
                    1.1.1) find_document(docfile.document.path)
                    1.1.2) Check for changes in name, content and size
                        1.1.2.1) Changes are detected: drc_client.update(doc_data)
                        1.1.2.2) Changes are not detected: Do nothing here
                1.2) Unlock document
        """
        # Create test docfile with read purpose
        doc_data, docfile = self.test_create_edit_document_file(delete=False)
        _uuid = docfile.uuid

        # Get filepaths to original document
        fp_to_protected = docfile.document.path
        fp_to_original = docfile.original_document.path

        # Check if files exist
        self.assertTrue(os.path.exists(fp_to_original))
        self.assertTrue(os.path.exists(fp_to_protected))

        # Check if folders exist
        dir_original = os.path.dirname(fp_to_original)
        dir_protected = os.path.dirname(fp_to_protected)
        self.assertTrue(os.path.exists(dir_original))
        self.assertTrue(os.path.exists(dir_protected))

        # Change filename of "protected" document to go down to 1.1.2.1
        _fp, extension = os.path.splitext(fp_to_protected)
        new_filename = f"gewijzigd{extension}"
        path_to_new_file = os.path.join(dir_protected, new_filename)
        os.rename(fp_to_protected, path_to_new_file)

        # Check if new file exists
        self.assertTrue(os.path.exists(path_to_new_file))

        # Get delete url
        delete_url = reverse("documentfile-detail", kwargs={"uuid": _uuid})

        # Update doc_data with new filename
        doc_data.update(
            {"bestandsnaam": new_filename,}
        )

        # Create mock call 1.1.2.1
        m.patch(docfile.drc_url, json=doc_data)

        # Create mock 1.2
        test_doc_unlock_url = f"{docfile.drc_url}/unlock"
        m.post(test_doc_unlock_url, json=[], status_code=204)

        # Call delete
        response = self.client.delete(delete_url)

        # Check response data
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check if docfile exists
        self.assertFalse(DocumentFile.objects.filter(uuid=_uuid).exists())

        # Check if files exist
        self.assertFalse(os.path.exists(fp_to_original))
        self.assertFalse(os.path.exists(fp_to_protected))

        # Check if folders exist
        self.assertFalse(os.path.exists(dir_original))
        self.assertFalse(os.path.exists(dir_protected))
