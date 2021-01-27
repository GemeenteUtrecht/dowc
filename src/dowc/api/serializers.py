import os

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from dowc.accounts.models import User
from dowc.core.constants import EXTENSION_HANDLER, DocFileTypes
from dowc.core.models import DocumentFile
from dowc.core.resource import WebDavResource
from dowc.core.tokens import document_token_generator


class DocumentFileSerializer(serializers.ModelSerializer):
    magic_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentFile
        fields = (
            "drc_url",
            "purpose",
            "magic_url",
            "uuid",
        )
        extra_kwargs = {
            "drc_url": {
                "write_only": True,
            },
            "purpose": {
                "required": True,
            },
            "uuid": {
                "read_only": True,
            },
        }

    def validate(self, data):
        validated_data = super().validate(data)

        # Search locked documents to check if someone is already editing
        # a document that is requested to be opened for editing.
        if validated_data["purpose"] == DocFileTypes.write:
            qs = DocumentFile.objects.filter(
                drc_url=validated_data["drc_url"],
                purpose=DocFileTypes.write,
            ).select_related("user")

            if qs.exists():
                locked_doc = get_object_or_404(qs)
                if locked_doc.user != self.context["request"].user:
                    # Document is opened and locked by someone else.
                    raise serializers.ValidationError(
                        _(
                            "Document {drc_url} has already been opened for editing and is currently locked by {user_id}."
                        ).format(
                            drc_url=validated_data["drc_url"],
                            user_id=locked_doc.user.username,
                        )
                    )
                else:
                    # Pass locked_doc on to viewset.perform_create to check if lock_doc is
                    # locked by current user.
                    validated_data["locked_doc"] = locked_doc

        return validated_data

    def create(self, validated_data):
        username = self.context["request"].user
        validated_data["user"] = get_object_or_404(User, username=username)
        return super().create(validated_data)

    def get_magic_url(self, obj) -> str:
        """
        The "magic" url consists of two major components.

        Roughly:
            Part 1: Pertains to MS Office URI Scheme.
            Part 2: URL with validation parameters and filepath to requested file.

        Part 1 is conditional. Part 2 is essential.

        In order to read/write certain files we make use of the Microsoft Office handlers
        that are installed whenever MS Office is installed.
        The handlers can be used to open files from a browser for a seemless user experience.

        For more information on the MS Office URI scheme, see this link:
        https://docs.microsoft.com/en-us/office/client-developer/office-uri-schemes

        ------------------------------------------------------------------------------
        Conditions for part 1:

        The requested file needs to have an extension that can be found in the
        in the EXTENSION_HANDLER. If this is not the case, the file can only be opened
        for reading for now.

        Information in part 1:

        A scheme name pertains to which particular MS Office app needs to be opened
        to read/write the requested file. Please see EXTENSION_HANDLER.
        A file can be read, in which case an open for view (ofv) command is invoked.
        A file can be written, in which case an open for edit (ofe) command is invoked.

        ------------------------------------------------------------------------------
        Information in part 2:

        UUID: UUID of documentfile object
        Token: token created by core.tokens.DocumentTokenGenerator
        Purpose: purpose of requesting file (can be read or write)
        Path: relative path to filename in webdav resource
        """
        fn, fext = os.path.splitext(obj.document.name)
        scheme_name = EXTENSION_HANDLER.get(fext, "")

        if not scheme_name:
            command_argument = ""
        else:
            if obj.purpose == DocFileTypes.read:
                command_argument = ":ofv|u|"
            else:
                command_argument = ":ofe|u|"

        full_filepath = obj.document.storage.path(obj.document.name)
        relative_filepath = os.path.relpath(full_filepath, WebDavResource.root)
        url = self.context["request"].build_absolute_uri(
            reverse(
                "core:webdav-document",
                kwargs={
                    "uuid": str(obj.uuid),
                    "token": document_token_generator.make_token(
                        obj.user, str(obj.uuid)
                    ),
                    "purpose": obj.purpose,
                    "path": obj.document.name,
                },
            )
        )

        return f"{scheme_name}{command_argument}{url}"