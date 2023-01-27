from django.utils.translation import gettext_lazy as _

from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings

from dowc.accounts.authentication import ApplicationTokenAuthentication
from dowc.accounts.permissions import HasTokenAuth
from dowc.core.constants import DocFileTypes
from dowc.core.models import DocumentFile
from dowc.core.utils import update_document

from .filters import IsOwnerOrApplicationFilterBackend
from .permissions import CanCloseDocumentFile
from .serializers import (
    DocumentFileSerializer,
    DocumentStatusSerializer,
    UnlockedDocumentSerializer,
)


@extend_schema_view(
    retrieve=extend_schema(
        summary=_("Retrieve documentfile"),
    ),
    list=extend_schema(
        summary=_("List documentfiles"),
        parameters=[
            OpenApiParameter(
                "drc_url",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                description=_("URL-reference of the document on the DRC"),
            ),
            OpenApiParameter(
                "info_url",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                description=_("Points to the origin of the document's usage."),
            ),
            OpenApiParameter(
                "purpose",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=sorted(list(DocFileTypes.values.keys())),
                description=_("Purpose of making the request."),
            ),
        ],
    ),
    create=extend_schema(summary=_("Create documentfile")),
    update=extend_schema(summary=_("Put documentfile")),
    partial_update=extend_schema(summary=_("Patch documentfile")),
    destroy=extend_schema(
        summary=_("Delete documentfile"),
        responses={200: UnlockedDocumentSerializer},
    ),
)
class DocumentFileViewset(viewsets.ModelViewSet):
    lookup_field = "uuid"
    queryset = DocumentFile.objects.all().select_related("user")
    serializer_class = DocumentFileSerializer
    filterset_fields = ("drc_url", "purpose", "info_url")
    authentication_classes = [
        ApplicationTokenAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = (HasTokenAuth | IsAuthenticated, CanCloseDocumentFile)
    filter_backends = [IsOwnerOrApplicationFilterBackend]

    def list(self, request, *args, **kwargs):
        """
        List the files available for local editing or viewing via WebDAV.

        Each file has a 'magic URL' pointing to the relevant MS Office protocol to
        open the file in a local MS Office client.

        """
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return response

    def create(self, request, *args, **kwargs):
        """
        Make a file available for local editing or viewing via WebDAV.

        The response contains a 'magic URL' understood by MS Office to view or edit
        the file in a local client.

        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check if writable document is already locked by current user.
        # If it is return magic_url instead of attempting to create a new
        # documentfile object.
        if serializer.validated_data["purpose"] == DocFileTypes.write:
            locked_doc = serializer.validated_data.pop("locked_doc", None)
            if locked_doc and locked_doc.user == request.user:
                return Response(status=status.HTTP_409_CONFLICT)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def destroy(self, request, *args, **kwargs):
        """
        Check in local edits and/or delete local WebDAV file.

        The response contains the URL and version of the resulting checked in document.

        """
        instance = self.get_object()
        self.perform_destroy(instance)

        serializer = UnlockedDocumentSerializer(instance=instance.api_document)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        if instance.purpose == DocFileTypes.write:
            updated_doc = instance.update_drc_document()
            if updated_doc:
                update_document(instance.unversioned_url, updated_doc)
            instance.unlock_drc_document()

        # Destroy instance
        super().perform_destroy(instance)

    @extend_schema(
        summary=_("Retrieve open documents."),
        request=DocumentStatusSerializer,
        responses={200: DocumentStatusSerializer},
    )
    @action(
        methods=["post"],
        detail=False,
    )
    def status(self, request, *args, **kwargs):
        serializer = DocumentStatusSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        queryset = self.get_queryset().filter(
            purpose=DocFileTypes.write,
            unversioned_url__in=[url["document"] for url in serializer.data],
        )
        serializer = DocumentStatusSerializer(queryset, many=True)
        return Response(serializer.data)
