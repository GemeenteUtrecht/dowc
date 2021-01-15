import os

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from doc.accounts.models import User
from doc.core.constants import EXTENSION_HANDLER, DocFileTypes
from doc.core.models import DocumentFile
from doc.core.resource import WebDavResource
from doc.core.tokens import document_token_generator


class DocumentFileSerializer(serializers.ModelSerializer):
    magic_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentFile
        fields = (
            "drc_url",
            "purpose",
            "magic_url",
        )
        extra_kwargs = {
            "drc_url": {
                "write_only": True,
            },
            "purpose": {
                "required": True,
            },
        }

    def validate(self, data):
        validated_data = super().validate(data)
        # Get locked documents to check if someone is already editing
        locked_docs = DocumentFile.objects.filter(
            drc_url=validated_data["drc_url"], purpose=DocFileTypes.write
        )
        if locked_docs:
            if locked_docs[0].user.username != self.context["request"].user.username:
                # Document is opened and locked by someone else.
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
