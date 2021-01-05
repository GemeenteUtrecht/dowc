from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django_sendfile import sendfile
from djangodav import views
from djangodav.acls import FullAcl
from djangodav.locks import DummyLock

from .models import DocumentFile
from .resource import WebDavResource
from .tokens import document_token_generator


class WebDAVPermissionMixin:
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        uuid = kwargs.pop("uuid", "")
        token = kwargs.pop("token", "")
        path = kwargs.pop("path", "")

        docfile = get_object_or_404(
            DocumentFile.objects.select_related("user"), uuid=uuid
        )

        if document_token_generator.check_token(docfile.user, uuid, token):
            return super().dispatch(request, path, *args, **kwargs)

        return HttpResponseUnAuthorized("Not Authorised")


class WebDavView(WebDAVPermissionMixin, views.DavView):
    resource_class = WebDavResource
    lock_class = DummyLock
    acl_class = FullAcl
