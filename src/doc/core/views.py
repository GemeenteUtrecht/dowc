from django.shortcuts import get_object_or_404, render
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.views import View

from sendfile import sendfile

from doc.accounts.models import User

from .models import DocumentFile
from .tokens import document_token_generator


class GetDocumentView(View):
    def get(self, request, uuid, token, filename):
        doc_file = get_object_or_404(
            DocumentFile.objects.select_related("user"), uuid=uuid
        )

        if document_token_generator.check_token(doc_file.user, uuid, token):
            return sendfile(request, doc_file.document.path)
