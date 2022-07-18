from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin

from .models import CoreConfig, DocumentFile


@admin.register(CoreConfig)
class CoreConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    actions = ["force_delete"]
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

    def force_delete(self, request, queryset):
        before = queryset.count()
        queryset.force_delete()
        after = queryset.count()
        if before - after == 1:
            msg = "1 Document file was"
        elif before - after != 0:
            msg = f"{before-after} Document files were"
        else:
            msg = "No Document files were"
        self.message_user(request, "%s force deleted." % msg)

    force_delete.short_description = _("Force delete selected Document files")

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
