from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.response import Response

from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile

from .serializers import DocumentFileSerializer


class DocumentFileViewset(viewsets.ModelViewSet):
    lookup_field = "uuid"
    queryset = DocumentFile.objects.all().select_related("user")
    serializer_class = DocumentFileSerializer
    filterset_fields = (
        "drc_url",
        "purpose",
    )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset()).filter(user=request.user)
        if qs.exists():
            page = self.paginate_queryset(qs)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            else:
                serializer = self.get_serializer(qs, many=True)
                return Response(serializer.data)

        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check if writable document is already locked by current user.
        # If it is return magic_url instead of attempting to create a new
        # documentfile object.
        if serializer.validated_data["purpose"] == DocFileTypes.write:
            locked_doc = serializer.validated_data.pop("locked_doc", None)

            if locked_doc and locked_doc.user == request.user:
                serializer = self.get_serializer(locked_doc)
                data = serializer.data
                return Response(status=status.HTTP_409_CONFLICT)

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
