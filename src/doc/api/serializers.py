import os

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from doc.accounts.models import User
from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile
from doc.core.tokens import document_token_generator


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

        if validated_data["purpose"] == DocFileTypes.edit:
            # Get locked documents to check if someone is already editing
            locked_docs = DocumentFile.objects.filter(
                drc_url=validated_data["drc_url"], purpose=DocFileTypes.edit
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
        if obj.purpose == DocFileTypes.read:
            prefix = "ms-word:ofv|u|"
        else:
            prefix = "ms-word:ofe|u|"

        url = self.context["request"].build_absolute_uri(
            reverse(
                "core:webdav-document",
                kwargs={
                    "uuid": str(obj.uuid),
                    "token": document_token_generator.make_token(
                        obj.user, str(obj.uuid)
                    ),
                    "path": obj.document.name,
                },
            )
        )

        return prefix + url
