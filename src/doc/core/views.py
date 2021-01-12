import os

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from djangodav import views
from djangodav.acls import ReadOnlyAcl
from djangodav.locks import DummyLock

from .acls import ReadAndWriteOnlyAcl
from .constants import DocFileTypes
from .models import DocumentFile
from .resource import WebDavResource
from .tokens import document_token_generator


class WebDAVPermissionMixin:
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        uuid = kwargs.pop("uuid", "")
        token = kwargs.pop("token", "")
        path = kwargs.pop("path", "")

        if "protected" in path:
            return HttpResponseForbidden("This folder is protected.")

        self.docfile = get_object_or_404(
            DocumentFile.objects.select_related("user"), uuid=uuid
        )

        if document_token_generator.check_token(self.docfile.user, uuid, token):
            # check purpose of object to set Acl
            if self.docfile.purpose == DocFileTypes.write:
                self.acl_class = ReadAndWriteOnlyAcl
            else:
                self.acl_class = ReadOnlyAcl

            return super().dispatch(request, path, *args, **kwargs)

        return HttpResponseForbidden("Link is invalid or expired.")


class WebDavView(WebDAVPermissionMixin, views.DavView):
    resource_class = WebDavResource
    lock_class = DummyLock
    acl_class = ReadOnlyAcl

    def options(self, request, path, *args, **kwargs):
        response = super().options(request, path, *args, **kwargs)

        # Necessary header for MS WebDAV Clients such as MS Office applications
        response["MS-Author-Via"] = "DAV"
        return response

    def put(self, request, path, *args, **kwargs):

        # If name is changed:
        if self.path != self.docfile.document.name:
            self.docfile.document.name = self.path
            self.docfile.filename = os.path.basename(self.path)
            self.docfile.save()

        return super().put(request, path, *args, **kwargs)
