from rest_framework import viewsets

from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile

from .serializers import DocumentFileSerializer


class DocumentFileViewset(viewsets.ModelViewSet):
    lookup_field = "uuid"
    queryset = DocumentFile.objects.all()
    serializer_class = DocumentFileSerializer

    def perform_destroy(self, instance):
        if instance.purpose == DocFileTypes.write:
            instance.update_drc_document()
            instance.unlock_drc_document()

        # Destroy instance
        super().perform_destroy(instance)
