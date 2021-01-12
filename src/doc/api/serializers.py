import os

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from doc.accounts.models import User
from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile
from doc.core.resource import WebDavResource
from doc.core.tokens import document_token_generator

EXTENSION_HANDLER = {
    ".doc": "ms-word",
    ".docm": "ms-word",
    ".docx": "ms-word",
    ".dot": "ms-word",
    ".dotm": "ms-word",
    ".dotx": "ms-word",
    ".htm": "ms-word",
    ".html": "ms-word",
    ".mht": "ms-word",
    ".mhtml": "ms-word",
    ".odt": "ms-word",
    ".pdf": "ms-word",
    ".rtf": "ms-word",
    ".txt": "ms-word",
    ".wps": "ms-word",
    ".xml": "ms-word",
    ".xps": "ms-word",
    ".csv": "ms-excel",
    ".dbf": "ms-excel",
    ".dif": "ms-excel",
    ".ods": "ms-excel",
    ".prn": "ms-excel",
    ".slk": "ms-excel",
    ".xla": "ms-excel",
    ".xlam": "ms-excel",
    ".xls": "ms-excel",
    ".xlsb": "ms-excel",
    ".xlsm": "ms-excel",
    ".xlsx": "ms-excel",
    ".xlt": "ms-excel",
    ".xltm": "ms-excel",
    ".xltx": "ms-excel",
    ".xlw": "ms-excel",
    ".emf": "ms-powerpoint",
    ".odp": "ms-powerpoint",
    ".pot": "ms-powerpoint",
    ".potm": "ms-powerpoint",
    ".potx": "ms-powerpoint",
    ".ppa": "ms-powerpoint",
    ".ppam": "ms-powerpoint",
    ".pps": "ms-powerpoint",
    ".ppsm": "ms-powerpoint",
    ".ppsx": "ms-powerpoint",
    ".ppt": "ms-powerpoint",
    ".pptm": "ms-powerpoint",
    ".pptx": "ms-powerpoint",
    ".thmx": "ms-powerpoint",
}


class DocumentFileSerializer(serializers.ModelSerializer):
    magic_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentFile
        fields = (
            "uuid",
            "drc_url",
            "purpose",
            "magic_url",
        )
        extra_kwargs = {
            "uuid": {
                "read_only": True,
            },
            "drc_url": {
                "write_only": True,
            },
            "purpose": {
                "required": True,
            },
        }

    def validate(self, data):
        validated_data = super().validate(data)

        if validated_data["purpose"] == DocFileTypes.write:
            # Get locked documents to check if someone is already editing
            locked_docs = DocumentFile.objects.filter(
                drc_url=validated_data["drc_url"], purpose=DocFileTypes.write
            )
            if locked_docs:
                raise serializers.ValidationError(
                    _(
                        "Document {drc_url} has already been opened for editing and is currently locked by {user_id}."
                    ).format(
                        drc_url=validated_data["drc_url"],
                        user_id=locked_docs[0].user.username,
                    )
                )

        return validated_data

    def create(self, validated_data):
        username = self.context["request"].user
        validated_data["user"] = get_object_or_404(User, username=username)
        return super().create(validated_data)

    def get_magic_url(self, obj) -> str:
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
        # url = self.context["request"].build_absolute_uri(
        url = "https://daniel.jprq.live" + reverse(
            "core:webdav-document",
            kwargs={
                "uuid": str(obj.uuid),
                "token": document_token_generator.make_token(obj.user, str(obj.uuid)),
                "purpose": obj.purpose,
                "path": f"{obj.document.name}",
            },
        )
        # )

        return f"{scheme_name}{command_argument}{url}"
