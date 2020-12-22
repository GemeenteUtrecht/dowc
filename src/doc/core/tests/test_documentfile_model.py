import json
import os
import uuid
from unittest.mock import patch

import requests_mock
from rest_framework.test import APITestCase

from doc.api.tests.mixins import AuthMixin
from doc.core.models import DocumentFile
from doc.core.tests.factories import DocumentFileFactory
from doc.core.tests.mixins import SetUpMockMixin


@requests_mock.Mocker()
class DocumentFileModelTests(SetUpMockMixin, AuthMixin, APITestCase):
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
            drc_url=self.test_doc_url, purpose="read", user=self.user
        )
        _uuid = docfile.uuid

        docfiles = DocumentFile.objects.filter(uuid=_uuid)
        self.assertTrue(docfiles.exists())

        self.assertEqual(docfile.drc_url, self.test_doc_url)
        self.assertEqual(docfile.purpose, "read")
        self.assertEqual(docfile.user.username, self.user.username)
        self.assertEqual(docfile.user.email, self.user.email)

        # Get filepaths to original document
        fp_to_protected = docfile.document.path
        fp_to_original = docfile.original_document.path

        # Check if files exist
        self.assertTrue(os.path.exists(fp_to_original))
        self.assertTrue(os.path.exists(fp_to_protected))

        # Check if document exists at path and with the right content
        with open(docfile.document.path) as open_doc:
            self.assertEqual(open_doc.read(), json.dumps(self.content))

        # Check if filename corresponds to filename on document
        saved_filename = os.path.basename(docfile.document.path)
        self.assertEqual(saved_filename, self.bestandsnaam)

        # Check if folders exist
        dir_original = os.path.dirname(fp_to_original)
        dir_protected = os.path.dirname(fp_to_protected)
        self.assertTrue(os.path.exists(dir_original))
        self.assertTrue(os.path.exists(dir_protected))
        # End of 2

        # 3
        self.assertEqual(len(m.request_history), 3)
        self.assertEqual(
            m.request_history[0].url, f"{self.DRC_URL}schema/openapi.yaml?v=3"
        )
        self.assertEqual(m.request_history[1].url, self.test_doc_url)

        # 4
        self.assertEqual(m.request_history[-1].url, self.test_doc_download_url)

        # Delete
        docfile.delete()

        # Check if files exist
        self.assertFalse(os.path.exists(fp_to_original))
        self.assertFalse(os.path.exists(fp_to_protected))

        # Check if folders exist
        self.assertFalse(os.path.exists(dir_original))
        self.assertFalse(os.path.exists(dir_protected))

    @patch("doc.core.models.logger")
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
        docfile = DocumentFileFactory.create(drc_url=self.test_doc_url, purpose="edit",)
        _uuid = docfile.uuid

        docfiles = DocumentFile.objects.filter(uuid=_uuid)
        # 1
        self.assertTrue(docfiles.exists())
        self.assertEqual(docfile.purpose, "edit")

        # 2
        self.assertEqual(len(m.request_history), 3)
        self.assertEqual(m.request_history[0].url, self.test_doc_lock_url)
        self.assertEqual(m.request_history[0].method, "POST")

        # 3
        self.assertTrue(len(docfile.lock) > 0)

        # 4
        self.assertEqual(m.request_history[1].url, self.test_doc_url)
        self.assertEqual(m.request_history[1].method, "GET")

        # 5
        self.assertEqual(m.request_history[2].url, self.test_doc_download_url)
        self.assertEqual(m.request_history[2].method, "GET")

        # Start of 6
        # Get filepaths to documents
        fp_to_protected = docfile.document.path
        fp_to_original = docfile.original_document.path

        # Get filepaths to folders
        dir_original = os.path.dirname(fp_to_original)
        dir_protected = os.path.dirname(fp_to_protected)

        # Change filename so that any(changes) returns True
        fp_to_protected = docfile.document.path
        _fp, extension = os.path.splitext(fp_to_protected)
        new_filename = f"gewijzigd{extension}"
        path_to_new_file = os.path.join(dir_protected, new_filename)
        os.rename(fp_to_protected, path_to_new_file)

        # Check if new file exists
        self.assertTrue(os.path.exists(path_to_new_file))

        # Update doc_data with new filename
        update_doc_data = {
            "bestandsnaam": new_filename,
        }

        # Create mock for call
        m.patch(docfile.drc_url, json={**self.doc_data, **update_doc_data})

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
        docfile.force_delete()
        self.assertEqual(m.request_history[-1].url, test_doc_unlock_url)
        self.assertEqual(m.request_history[-1].method, "POST")
        # End of 8

        # 9
        # Check if files exist
        self.assertFalse(os.path.exists(fp_to_original))
        self.assertFalse(os.path.exists(fp_to_protected))

        # Check if folders exist
        self.assertFalse(os.path.exists(dir_original))
        self.assertFalse(os.path.exists(dir_protected))
