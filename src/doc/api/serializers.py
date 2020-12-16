from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from doc.accounts.models import User
from doc.core.models import DocumentFile
from doc.core.tokens import document_token_generator


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "email",
        )


class DocumentFileSerializer(serializers.ModelSerializer):
    user = UserSerializer(
        help_text=_("User that is requesting the document."), required=True,
    )
    purpose = serializers.ChoiceField(choices=("read", "edit"), required=True)

    class Meta:
        model = DocumentFile
        fields = (
            "uuid",
            "url",
            "user",
            "purpose",
        )
        extra_kwargs = {
            "uuid": {"read_only": True,},
            "url": {"write_only": True,},
        }

    def validate(self, data):
        validated_data = super().validate(data)

        docfiles = DocumentFile.objects.filter(url=validated_data["url"])
        if docfiles:
            raise serializers.ValidationError(
                _(
                    "Document has already been opened and is currently locked by {email}."
                ).format(email=docfiles[0].user_email)
            )

        return validated_data

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user, created = User.objects.get_or_create(**user_data)
        if created:
            user.password = BaseUserManager.make_random_password(30)
            user.save()

        validated_data["user"] = user
        return super().create(validated_data)
