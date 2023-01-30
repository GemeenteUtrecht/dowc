from rest_framework.permissions import BasePermission

from dowc.accounts.models import ApplicationToken
from dowc.core.models import DocumentFile

###############################
#   Application Permissions   #
###############################


class CanCloseDocumentFile(BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.method != "DELETE":
            return True
        if (
            request.auth
            and isinstance(request.auth, ApplicationToken)
            and request.auth.can_force_close_documents
        ):
            return True

        return DocumentFile.objects.filter(user=request.user).exists()

    def has_object_permission(self, request, view, obj):
        if request.method != "DELETE":
            return True
        if request.user and (request.user == obj.user or request.user.is_superuser):
            return True
        if (
            request.auth
            and isinstance(request.auth, ApplicationToken)
            and request.auth.can_force_close_documents
        ):
            return True
        return False
