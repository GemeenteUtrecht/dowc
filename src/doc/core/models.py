import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext_lazy as _

from doc.accounts.models import User

from .constants import DocFileTypes

sendfile_storage = FileSystemStorage(location=settings.SENDFILE_ROOT)


def create_original_document_path(instance, filename):
    return "/".join(["original", instance.uuid.hex, filename])


def create_protect_document_path(instance, filename):
    return "/".join([instance.uuid.hex, filename])


class DocumentFile(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text=_(
            "This unique UUID is used to identify the edited document in case the name of the document is changed."
        ),
    )
    created = models.DateTimeField(_("created"), auto_now_add=True)
    original_document = models.FileField(
        _("original document file"),
        upload_to=create_original_document_path,
        help_text=_(
            "The original document is used to check if the document is edited before updating the document on the Documenten API."
        ),
    )
    document = models.FileField(
        _("This document is to be edited or read."),
        upload_to=create_protect_document_path,
        storage=sendfile_storage,
        help_text=_("This document can be edited directly by MS Office applications."),
    )
    lock = models.CharField(
        _("lock hash"),
        help_text=_(
            "Lock that is provided by Documenten API when you need to edit a document."
        ),
        max_length=100,
        default="",
        blank=True,
    )

    purpose = models.CharField(
        max_length=4,
        choices=DocFileTypes.choices,
        default="read",
        help_text=_("Purpose of requesting the document."),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, help_text=_("User requesting the document.")
    )

    drc_url = models.URLField(
        _("DRC URL"),
        help_text=_(
            "URL reference to the source document in the Documents API. May "
            "include the 'versie' querystring parameter."
        ),
        max_length=1000,
    )

    class Meta:
        verbose_name = _("Document file")
        verbose_name_plural = _("Document files")

    def __str__(self):
        if not self.pk:
            return "Pending creation"

        return self.drc_url

    def filename(self):
        return f"{os.path.basename(self.document.path)}"

    filename.short_description = _("Filename")

    def username(self):
        return self.user.username

    username.short_description = _("Username")
