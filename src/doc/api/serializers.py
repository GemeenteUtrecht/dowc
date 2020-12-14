from rest_framework import serializers

from doc.core.models import DocumentFile


class DocumentFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentFile
        fields = (
            "user_email",
            "username",
            "url",
        )

    def validate(self, data):
        validated_data = super().validate(data)
        docfiles = DocumentFile.objects.filter(url=validated_data["url"])
        if docfiles:
            raise serializers.ValidationError(
                _("Document has already been opened and locked by {email}.").format(
                    email=docfiles[0].user_email
                )
            )

        return validated_data
