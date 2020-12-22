from django.shortcuts import get_object_or_404
from django.views import View

from sendfile import sendfile

from .models import DocumentFile
from .tokens import document_token_generator


class GetDocumentView(View):
    def get(self, request, uuid, token, filename):
        doc_file = get_object_or_404(
            DocumentFile.objects.select_related("user"), uuid=uuid
        )

        if document_token_generator.check_token(doc_file.user, uuid, token):
            return sendfile(request, doc_file.document.path)
