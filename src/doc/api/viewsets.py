from rest_framework import viewsets
from rest_framework.response import Response

from doc.core.constants import EXTENSION_HANDLER, DocFileTypes
from doc.core.models import DocumentFile

from .serializers import DocumentFileSerializer


class DocumentFileViewset(viewsets.ModelViewSet):
    lookup_field = "uuid"
    queryset = DocumentFile.objects.all()
    serializer_class = DocumentFileSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get locked documents to check if someone is already editing
        locked_docs = DocumentFile.objects.filter(
            drc_url=serializer.validated_data["drc_url"], purpose=DocFileTypes.write
        )
        if locked_docs:
            instance = locked_docs[0]
            # If document is locked by current user but editing has not yet finished - provide new magic url.
            if instance.user.username == request.user.username:
                serializer = self.get_serializer(instance)
                return Response(serializer.data)

            # Else document is opened and locked by someone else.
            raise serializers.ValidationError(
                _(
                    "Document {drc_url} has already been opened for editing and is currently locked by {user_id}."
                ).format(
                    drc_url=serializer.validated_data["drc_url"],
                    user_id=instance.user.username,
                )
            )

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
