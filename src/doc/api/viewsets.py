import base64
import os
import shutil

from django.core.files.base import ContentFile

from rest_framework import mixins, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from doc.core.models import DocumentFile
from doc.core.utils import (
    get_document,
    get_document_content,
    lock_document,
    unlock_document,
    update_document,
)

from .serializers import DocumentFileSerializer
from .utils import find_document


class DocumentFileViewset(viewsets.ModelViewSet):
    lookup_field = "uuid"
    queryset = DocumentFile.objects.all()
    serializer_class = DocumentFileSerializer

    def perform_create(self, serializer):
        # Lock the document before getting it ensures nobody can steal
        # it before we get a chance to work with it.
        drc_url = serializer.validated_data["drc_url"]

        lock = ""
        if serializer.validated_data["purpose"] == "edit":
            lock = lock_document(drc_url)

        # Get document
        document = get_document(drc_url)

        # Get content [bytes]
        content = get_document_content(document.inhoud)

        # Create temporary doc in memory with contentfile
        temp_doc = ContentFile(content, name=document.bestandsnaam)

        # Create object
        serializer.save(
            lock=lock, original_document=temp_doc, document=temp_doc,
        )

    def perform_destroy(self, instance):
        # Compare original document with (new) document to see if it's
        # actually edited before pushing an update to Documenten API.

        if instance.purpose == "edit":
            # Get original document
            with open(instance.original_document.path, "rb") as ori_doc:
                original_content = ori_doc.read()

            # Get (potentially) edited document
            path_to_document = find_document(instance.document.path)
            edi_fn = os.path.basename(path_to_document)

            # Store edited document to ContentFile
            with open(path_to_document, "rb") as edi_doc:
                edited_content = edi_doc.read()
                edited_document = ContentFile(edited_content, name=edi_fn)

            # Check for any changes in size, name or content
            ori_fn = os.path.basename(instance.original_document.path)
            name_change = ori_fn != edi_fn
            size_change = instance.original_document.file.size != edited_document.size
            content_change = original_content != edited_content

            if any([name_change, size_change, content_change]):
                data = {
                    "auteur": instance.user.username,
                    "bestandsomvang": edited_document.size,
                    "bestandsnaam": edi_fn,
                    "inhoud": base64.b64encode(edited_content).decode("utf-8"),
                    "lock": instance.lock,
                }

                # Update document
                update_document(instance.drc_url, data)

            # Unlock document
            unlock_document(instance.drc_url, instance.lock)

        # Get all folders related to instance ...
        document_paths = [instance.original_document.path, instance.document.path]

        # ... and delete them with their contents
        for path in document_paths:
            folder_path = os.path.dirname(path)
            shutil.rmtree(folder_path)

        # Destroy instance
        super().perform_destroy(instance)
