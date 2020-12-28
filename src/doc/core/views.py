from django.shortcuts import get_object_or_404
from django.views import View

from django_sendfile import sendfile

from .models import DocumentFile
from .tokens import document_token_generator


class GetDocumentView(View):
    def get(self, request, uuid, token, filename):
        docfile = get_object_or_404(
            DocumentFile.objects.select_related("user"), uuid=uuid
        )

        if document_token_generator.check_token(docfile.user, uuid, token):
            return sendfile(request, docfile.storage.path(docfile.document.name))

        else:
            raise PermissionDenied("You don't have permission to open the file.")
