import os

from rest_framework.permissions import BasePermission

from dowc.core.constants import ResourceSubFolders
from dowc.core.models import get_parent_folder

from .tokens import document_token_generator

SAFE_METHODS = ("HEAD", "OPTIONS")


class UserOwnsDocumentFile(BasePermission):
    message = "User is not allowed to open this document."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        obj = view.get_object()
        return self.has_object_permission(request, view, obj)

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.user == obj.user


class PathIsAllowed(BasePermission):
    message = "Path is not allowed."

    def has_permission(self, request, view):
        ## Check if folder is subfolder of appropriate parent folder (.../<hash>/<public>)
        # Get relative path of parent folder
        obj = view.get_object()
        rel_path_parent = get_parent_folder(obj, ResourceSubFolders.public)

        # Make sure folders other than ../<hash>/<public> can't be accessed.
        if not view.kwargs["path"].startswith(rel_path_parent):
            return False

        if os.path.normpath(view.kwargs["path"]) == os.path.normpath(rel_path_parent):
            if request.method.lower() not in ["options", "propfind"]:
                return False

        return True


class TokenIsValid(BasePermission):
    message = "Token is invalid (expired or tampered with)."

    def has_permission(self, request, view):
        token = view.kwargs.get("token")
        if token and not document_token_generator.check_token(
            request.user, view.kwargs["uuid"], token
        ):
            return False
        return True
