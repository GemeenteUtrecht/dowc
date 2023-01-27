from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from hijack_admin.admin import HijackUserAdminMixin

from .models import ApplicationToken, User


@admin.register(User)
class _UserAdmin(UserAdmin, HijackUserAdminMixin):
    list_display = UserAdmin.list_display + ("hijack_field",)


@admin.register(ApplicationToken)
class ApplicationTokenAuthAdmin(admin.ModelAdmin):
    list_display = (
        "token",
        "contact_person",
        "organization",
        "administration",
        "application",
    )
    readonly_fields = ("token",)
    date_hierarchy = "created"
    extra = 0
