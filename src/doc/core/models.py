import base64
import logging
import os
import shutil
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext_lazy as _

from doc.accounts.models import User

from .constants import DocFileTypes
from .managers import DeletionManager
from .utils import (
    find_document,
    get_document,
    get_document_content,
    lock_document,
    unlock_document,
    update_document,
)

logger = logging.getLogger(__name__)
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

    deletion = models.BooleanField(
        _("Delete"),
        help_text=_(
            "The document associated to this object has been updated on the DRC and is ready for deletion."
        ),
        default=False,
    )

    objects = DeletionManager()

    class Meta:
        verbose_name = _("Document file")
        verbose_name_plural = _("Document files")

    def __str__(self):
        if not self.pk:
            return "Pending creation"

        return self.drc_url

    ### Protect objects that have locked a document in the DRC
    def delete(self):
        if self.deletion or self.purpose == "read":
            super().delete()

        else:
            logger.warning(
                "Object: DocumentFile {_uuid} has not been marked for deletion and has locked {drc_url} with lock {lock}.".format(
                    _uuid=self.uuid, drc_url=self.drc_url, lock=self.lock
                ),
            )

    ### Get document on DRC and set it to document and original_document
    def get_temp_document(self):
        document = get_document(self.drc_url)
        content = get_document_content(document.inhoud)
        temp_doc = ContentFile(content, name=document.bestandsnaam)
        return temp_doc

    ### Unlock document on DRC
    def unlock_drc_document(self):
        unlock_document(self.drc_url, self.lock)
        self.deletion = True
        self.save()

    ### Update document on DRC
    def update_drc_document(self):
        # Get original document
        with open(self.original_document.path, "rb") as ori_doc:
            original_content = ori_doc.read()

        # Get (potentially) edited document
        path_to_document = find_document(self.document.path)
        edi_fn = os.path.basename(path_to_document)

        # Store edited document to ContentFile
        with open(path_to_document, "rb") as edi_doc:
            edited_content = edi_doc.read()
            edited_document = ContentFile(edited_content, name=edi_fn)

        # Check for any changes in size, name or content
        ori_fn = os.path.basename(self.original_document.path)
        name_change = ori_fn != edi_fn
        size_change = self.original_document.file.size != edited_document.size
        content_change = original_content != edited_content

        if any([name_change, size_change, content_change]):
            data = {
                "auteur": self.user.username,
                "bestandsomvang": edited_document.size,
                "bestandsnaam": edi_fn,
                "inhoud": base64.b64encode(edited_content).decode("utf-8"),
                "lock": self.lock,
            }

            # Update document
            update_document(self.drc_url, data)

    ### For model admin
    def filename(self):
        return f"{os.path.basename(self.document.path)}"

    filename.short_description = _("Filename")

    def username(self):
        return self.user.username

    username.short_description = _("Username")


@receiver(pre_save, sender=DocumentFile)
def set_documents_and_lock(sender, instance, **kwargs):
    if not instance.pk:
        # Get document data from DRC
        temp_doc = instance.get_temp_document()

        # Save it to document and original document fields
        instance.document = temp_doc
        instance.original_document = temp_doc

        # Lock document if purpose is to edit
        if instance.purpose == "edit":
            instance.lock = lock_document(instance.drc_url)


@receiver(post_delete, sender=DocumentFile)
def delete_associated_folders_and_files(sender, instance, **kwargs):
    # Get all folders related to instance ...
    document_paths = [instance.original_document.path, instance.document.path]

    # ... and delete them with their contents
    for path in document_paths:
        folder_path = os.path.dirname(path)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
