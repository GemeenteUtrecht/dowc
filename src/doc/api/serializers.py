from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema_field
from rest_framework import serializers

from doc.accounts.models import User
from doc.core.constants import DocFileTypes
from doc.core.models import DocumentFile
from doc.core.tokens import document_token_generator


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username",)
        extra_kwargs = {
            "username": {"validators": [UnicodeUsernameValidator()],},
        }


class DocumentFileSerializer(serializers.ModelSerializer):
    user = UserSerializer(
        help_text=_("User that is requesting the document."), read_only=True
    )
    magic_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentFile
        fields = (
            "uuid",
            "drc_url",
            "user",
            "purpose",
            "magic_url",
        )
        extra_kwargs = {
            "uuid": {"read_only": True,},
            "drc_url": {"write_only": True,},
            "purpose": {"required": True,},
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
        user = self.context["request"].user
        user, created = User.objects.update_or_create(username=user)
        if created:
            user.set_password(BaseUserManager.make_random_password(30))
            user.save()

        validated_data["user"] = user
        return super().create(validated_data)

    @extend_schema_field(OpenApiTypes.STR)
    def get_magic_url(self, obj):
        return self.context["request"].build_absolute_uri(
            reverse(
                "core:get-document",
                kwargs={
                    "uuid": str(obj.uuid),
                    "token": document_token_generator.make_token(
                        obj.user, str(obj.uuid)
                    ),
                    "filename": obj.filename,
                },
            )
        )
