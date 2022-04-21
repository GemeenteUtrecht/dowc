import logging
import os
from typing import Optional

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from djangodav import views
from djangodav.acls import ReadOnlyAcl

from .acls import ReadAndWriteOnlyAcl
from .constants import DocFileTypes, ResourceSubFolders
from .locks import WebDAVLock
from .models import DocumentFile, get_parent_folder
from .resource import WebDavResource
from .tokens import document_token_generator

logger = logging.getLogger(__name__)


class WebDAVPermissionMixin:
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        logger.debug("Request headers for %s: %r", request.path, request.headers)
        _uuid = kwargs.get("uuid")

        ## Check if object exists based on uuid
        docfile = self.get_documentfile(_uuid)

        ## Check if folder is subfolder of appropriate parent folder (.../<username>/<public>)
        # Get relative path of parent folder
        rel_path_parent = get_parent_folder(docfile, ResourceSubFolders.public)
        path = kwargs.pop("path")

        # Make sure folders other than ../username/<public> can't be accessed.
        if not path.startswith(rel_path_parent):
            message = f"{request.path} is protected and can't be accessed, changed or deleted."
            logger.warning(message, extra={"status_code": 403, "request": request})
            return HttpResponseForbidden(message)

        ## Parent directory needs to protected in the case that a request with method other than OPTIONS is done.
        if os.path.normpath(path) == os.path.normpath(rel_path_parent):
            if request.method.lower() not in ["options", "propfind"]:
                return self.http_method_not_allowed(request, *args, **kwargs)

        ## Check token
        token = kwargs.pop("token")
        if document_token_generator.check_token(docfile.user, _uuid, token):
            # check purpose of object to set Acl
            if docfile.purpose == DocFileTypes.write:
                self.acl_class = ReadAndWriteOnlyAcl
            else:
                self.acl_class = ReadOnlyAcl

            return super().dispatch(request, path, *args, **kwargs)

        message = f"Token: {token} in URL is invalid or expired."
        logger.warning(message, extra={"status_code": 403, "request": request})
        return HttpResponseForbidden(message)


class WebDavView(WebDAVPermissionMixin, views.DavView):
    resource_class = WebDavResource
    lock_class = WebDAVLock

    def get_documentfile(self, _uuid) -> Optional[DocumentFile]:
        return get_object_or_404(
            DocumentFile.objects.select_related("user"), uuid=_uuid
        )

    def options(self, request, path, *args, **kwargs):
        response = super().options(request, path, *args, **kwargs)

        # Necessary header for MS WebDAV Clients such as MS Office applications
        response["MS-Author-Via"] = "DAV"
        return response

    def put(self, request, path, *args, **kwargs):
        # Update relevant model fields if name is changed:
        _uuid = kwargs.get("uuid")
        docfile = self.get_documentfile(_uuid)
        if self.path != docfile.document.name:
            docfile.document.name = self.path
            docfile.filename = os.path.basename(self.path)
            docfile.changed_name = True
            docfile.save()

        return super().put(request, path, *args, **kwargs)
