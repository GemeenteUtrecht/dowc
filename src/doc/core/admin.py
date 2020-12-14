from django.contrib import admin

from .models import DocumentFile


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    search_field = ["user_email", "url", "filename"]
    list_select_related = True
