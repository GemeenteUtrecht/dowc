from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from djangodav.acls import ReadOnlyAcl
from djangodav.utils import WEBDAV_NSMAP, rfc1123_date
from lxml import etree
from rest_framework import exceptions, status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.views import APIView, set_rollback

from .acls import ReadAndWriteOnlyAcl
from .constants import DocFileTypes


def exception_handler(exc, context):
    """
    Taken from rest_framework.views.exception_handler

    Because the WebDAV client requires a specific protocol to authenticate,
    the headers are allowed to be defined in the auth_header and are unpacked here.
    """
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    headers = {}
    if isinstance(exc, exceptions.APIException):
        if getattr(exc, "auth_header", None):
            for header, value in exc.auth_header.items():
                headers[header] = value
        if getattr(exc, "wait", None):
            headers["Retry-After"] = "%d" % exc.wait

        if getattr(exc, "status_code", None):
            status = exc.status_code
        else:
            status = 400

        set_rollback()
        return HttpResponse(exc.detail, status=status, headers=headers)

    return None


class WebDAVRestViewMixin:
    view = APIView

    def get_exception_handler_context(self):
        return self.view.get_exception_handler_context(self)

    def perform_authentication(self, request):
        return self.view.perform_authentication(self, request)

    def get_authenticators(self):
        return self.view.get_authenticators(self)

    def get_authenticate_header(self, request):
        return self.view.get_authenticate_header(self, request)

    def get_exception_handler(self):
        """
        Returns the exception handler that this view uses.
        """
        return exception_handler

    def handle_exception(self, exc):
        """
        Handle any exception that occurs, by returning an appropriate response,
        or re-raising the error.
        """
        if isinstance(
            exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)
        ):
            exc.auth_header = self.get_authenticate_header(self.request)
            exc.status_code = status.HTTP_403_FORBIDDEN

        exception_handler = self.get_exception_handler()

        context = self.get_exception_handler_context()
        response = exception_handler(exc, context)

        if response is None:
            self.raise_uncaught_exception(exc)

        response.exception = True
        return response

    def permission_denied(self, request, message=None, code=None):
        return self.view.permission_denied(self, request, message=message, code=code)

    def get_permissions(self):
        return self.view.get_permissions(self)

    def check_permissions(self, request):
        return self.view.check_permissions(self, request)

    def initial(self, request, *args, **kwargs):
        if path := self.kwargs.get("path"):
            self.base_url = self.request.META["PATH_INFO"][: -len(path)]
        else:
            self.kwargs["path"] = "/"
            self.request.META["PATH_INFO"]

        # Set xbody response
        self.set_xbody()

        ## Check if object exists
        obj = self.get_object()

        # Set acl_class based on purpose for object's existence
        self.set_acl_class(obj)

        # Check permissions
        self.perform_authentication(self.request)
        self.check_permissions(self.request)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.request = Request(
            request,
            authenticators=self.get_authenticators(),
        )
        try:
            self.initial(self.request, *args, **kwargs)

            if self.request.method.upper() in self._allowed_methods():
                handler = getattr(
                    self, self.request.method.lower(), self.http_method_not_allowed
                )
            else:
                handler = self.http_method_not_allowed

            self.path = self.kwargs.pop("path")
            response = handler(self.request, self.path, *args, **kwargs)
        except APIException as exc:
            response = self.handle_exception(exc)

        response = self.set_server_headers(response)
        return response

    def set_acl_class(self, obj):
        if obj.purpose == DocFileTypes.write:
            self.acl_class = ReadAndWriteOnlyAcl
        else:
            self.acl_class = ReadOnlyAcl

    def set_xbody(self):
        meta = self.request.META.get
        self.xbody = self.kwargs["xbody"] = None
        if (
            self.request.method.lower() != "put"
            and "/xml" in meta("CONTENT_TYPE", "")
            and meta("CONTENT_LENGTH", 0) != ""
            and int(meta("CONTENT_LENGTH", 0)) > 0
        ):
            self.xbody = self.kwargs["xbody"] = etree.XPathDocumentEvaluator(
                etree.parse(self.request, etree.XMLParser(ns_clean=True)),
                namespaces=WEBDAV_NSMAP,
            )

    def set_server_headers(self, response):
        if not "Allow" in response:
            methods = self._allowed_methods()
            if methods:
                response["Allow"] = ", ".join(methods)

        if not "Date" in response:
            response["Date"] = rfc1123_date(now())
        if self.server_header:
            response["Server"] = self.server_header

        if self.request.method == "OPTIONS":
            # Necessary header for MS WebDAV Clients such as MS Office applications
            response["MS-Author-Via"] = "DAV"
        return response
