import os
from typing import Optional

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from djangodav import views
from rest_framework.permissions import IsAuthenticated

from dowc.core.authentication import WebDavADFSAuthentication
from dowc.core.utils import clean_token

from .locks import WebDAVLock
from .mixins import WebDAVRestViewMixin
from .models import CoreConfig, DocumentFile, DocumentLock
from .permissions import PathIsAllowed, TokenIsValid, UserOwnsDocumentFile
from .resource import WebDavResource


class WebDavView(WebDAVRestViewMixin, views.DavView):
    resource_class = WebDavResource
    lock_class = WebDAVLock

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if CoreConfig.get_solo().webdav_adfs_authentication:
            self.authentication_classes = (WebDavADFSAuthentication,)
            self.permission_classes = (
                IsAuthenticated,
                UserOwnsDocumentFile,
                PathIsAllowed,
                TokenIsValid,
            )
        else:
            self.authentication_classes = []
            self.permission_classes = (
                PathIsAllowed,
                TokenIsValid,
            )

    def get_object(self) -> Optional[DocumentFile]:
        return get_object_or_404(
            DocumentFile.objects.select_related("user"), uuid=self.kwargs["uuid"]
        )

    def put(self, request, path, *args, **kwargs):
        # Update relevant model fields if name is changed:
        docfile = self.get_object()
        if path != docfile.document.name:
            docfile.document.name = path
            docfile.filename = os.path.basename(path)
            docfile.changed_name = True
            docfile.save()

        response = super().put(request, path, *args, **kwargs)
        return response

    def lock(self, request, path, *args, **kwargs):
        if token_header := request.headers.get("If"):
            token = clean_token(token_header)
            locks = DocumentLock.objects.filter(token=token)
            if locks.exists():
                return HttpResponse(status=200)
            return HttpResponse(status=400)
        else:
            return super().lock(request, path, *args, **kwargs)
