import uuid

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext_lazy as _

from doc.conf.includes import base as settings

sendfile_storage = FileSystemStorage(location=settings.SENDFILE_ROOT)


def create_original_document_path(instance, filename):
    return "/".join(["original", instance.uuid.hex, filename])


def create_protect_document_path(instance, filename):
    return "/".join([instance.uuid.hex, filename])


class DocumentFile(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False,)
    created = models.DateTimeField(_("created"), auto_now_add=True)
    original_document = models.FileField(upload_to=create_original_document_path)
    document = models.FileField(
        upload_to=create_protect_document_path, storage=sendfile_storage
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
    username = models.CharField(
        _("Username"),
        help_text=_("Username of user requesting document."),
        max_length=255,
    )
    user_email = models.EmailField(
        _("User email address"),
        help_text=_("Email address of user requesting document."),
    )
    url = models.URLField(
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

        return self.url
