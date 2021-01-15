from rest_framework import status, viewsets
from rest_framework.response import Response

from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile

from .serializers import DocumentFileSerializer


class DocumentFileViewset(viewsets.ModelViewSet):
    lookup_field = "uuid"
    queryset = DocumentFile.objects.all()
    serializer_class = DocumentFileSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Return magic url if writable document is already locked by current user
        if serializer.validated_data["purpose"] == DocFileTypes.write:
            locked_docs = self.queryset.filter(
                drc_url=serializer.validated_data["drc_url"],
                purpose=serializer.validated_data["purpose"],
            )
            if locked_docs.exists():
                if locked_docs[0].user.username == request.user.username:
                    serializer = self.get_serializer(locked_docs[0])
                    data = serializer.data
                    return Response(data)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_destroy(self, instance):
        if instance.purpose == DocFileTypes.write:
            instance.update_drc_document()
            instance.unlock_drc_document()

        # Destroy instance
        super().perform_destroy(instance)
