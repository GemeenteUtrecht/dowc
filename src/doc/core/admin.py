import os

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import DocumentFile


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    readonly_fields = ["uuid", "created"]

    list_display = [
        "filename",
        "uuid",
        "username",
        "purpose",
        "url",
    ]
    search_field = ["username", "url", "document"]
    list_select_related = ("user",)
