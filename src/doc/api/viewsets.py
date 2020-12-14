import base64

from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from doc.core.models import DocumentFile
from doc.core.utils import get_document, lock_document

from .serializers import DocumentFileSerializer


class DocumentFileViewset(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    queryset = DocumentFile.objects.all()
    serializer = DocumentFileSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        url = serializer.validated_data["url"]
        # Lock the document before getting it ensures nobody can steal
        # it before we get a chance to work with it.
        lock = lock_document(url)

        # Get document
        document = get_document(url)

        with open(document.bestandsnaam, "r") as temp_doc:
            temp_doc.write(base64.base64decode(document.inhoud))

            serializer.save(lock=lock, document=temp_doc)
