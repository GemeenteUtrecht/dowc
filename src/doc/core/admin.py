from django.contrib import admin

from .models import DocumentFile


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    readonly_fields = ["uuid", "created"]

    list_display = [
        "filename",
        "uuid",
        "username",
        "purpose",
        "drc_url",
    ]
    search_field = ["username", "drc_url", "document"]
    list_select_related = ("user",)
