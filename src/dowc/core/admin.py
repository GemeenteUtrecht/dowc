from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import DocumentFile


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    readonly_fields = (
        "uuid",
        "created",
        "filename",
        "drc_url",
        "original_document_file_location",
        "document_file_location",
        "lock",
    )

    list_display = (
        "user",
        "uuid",
        "filename",
        "purpose",
        "drc_url",
    )
    search_field = (
        "username",
        "drc_url",
        "document",
    )
    list_select_related = ("user",)

    exclude = (
        "document",
        "original_document",
    )

    def original_document_file_location(self, obj):
        return obj.original_document.name

    original_document_file_location.short_description = _("Original document location")

    def document_file_location(self, obj):
        return obj.document.name

    document_file_location.short_description = _("Document location")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("purpose",)
        return self.readonly_fields
