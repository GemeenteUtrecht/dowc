from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from .data import EmailData


class EmailSerializer(APIModelSerializer):
    email = serializers.EmailField(
        source="user.email", help_text=_("The email address of the receiver.")
    )
    info_url = serializers.URLField(
        help_text=_("Points to the origin of the document's usage.")
    )
    name = serializers.SerializerMethodField(help_text=_("Name of receiver."))

    class Meta:
        model = EmailData
        fields = (
            "email",
            "filename",
            "info_url",
            "name",
        )

    def get_name(self, obj):
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        if obj.user.username:
            return obj.user.username
        return _("user")
