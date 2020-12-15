import base64
import glob
import os

from django.core.files.base import ContentFile

from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from doc.core.models import DocumentFile
from doc.core.utils import (
    get_document,
    get_document_content,
    lock_document,
    unlock_document,
)

from .serializers import DocumentFileSerializer


def find_document(path):
    # In case filename has changed
    path = "/".join(path.split("/")[:-1] + ["*"])
    filenames = glob.glob(path)
    if filenames:
        return filenames[0]


class DocumentFileViewset(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    queryset = DocumentFile.objects.all()
    serializer_class = DocumentFileSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        url = serializer.validated_data["url"]
        # Lock the document before getting it ensures nobody can steal
        # it before we get a chance to work with it.
        print("CALL LOCK")
        # lock = lock_document(url)

        # Get document
        document = get_document(url)

        # Get content [bytes]
        content = get_document_content(document.inhoud)

        # Create temporary doc in memory with contentfile
        temp_doc = ContentFile(content, name=document.bestandsnaam)

        # Create object
        serializer.save(
            lock="lock", original_document=temp_doc, document=temp_doc,
        )

    def perform_destroy(self, instance):
        # Compare original document with (new) document to see if it's
        # actually edited before pushing an update to Documenten API.

        # Get (potentially) edited document
        path_to_document = find_document(instance.document.url)
        filename = path_to_document.split("/")[-1]
        # Open document
        with open(path_to_document, "rb") as document:
            edited_document = ContentFile(document.read(), name=filename)

        original_document = instance.original_document
        name_change = original_document.name != edited_document.name
        size_change = original_document.size != edited_document.size
        content_change = original_document.read() != edited_document.read()
        if any([name_change, size_change, content_change,]):
            data = {
                "auteur": instance.username,
                "bestandsomvang": document.size,
                "bestandsnaam": document.name,
                "content": base64.b64encode(document.read()).decode("utf-8"),
                "lock": instance.lock,
            }

            print("CALL UPDATE")
            print(original_document.size, edited_document.size)
            print(original_document.name, edited_document.name)
            print(original_document.read())
            print("*" * 10)
            print(edited_document.read())

            # Update document
            #
            # update_document(instance.url, data)

            # If name changed -> save it to model so that file gets deleted on destroy instance
            if name_change:
                instance.document.name = filename
                instance.save()

        print("CALL UNLOCK")
        # Unlock document
        #
        # unlock_document(instance.url)

        # Destroy instance
        super().perform_destroy(instance)
