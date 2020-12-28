import base64
import logging
import os
import shutil
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext_lazy as _

from privates.fields import PrivateMediaFileField

from doc.accounts.models import User

from .constants import DocFileTypes
from .managers import DeleteQuerySet
from .utils import (
    get_document,
    get_document_content,
    lock_document,
    unlock_document,
    update_document,
)

logger = logging.getLogger(__name__)


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
    safe_for_deletion = models.BooleanField(
        _("Safe for deletion"),
        help_text=_(
            "The document associated to this object has been updated on the DRC and is ready for deletion."
        ),
        default=False,
    )
    document = PrivateMediaFileField(
        _("This document is to be edited or read."),
        help_text=_("This document can be edited directly by MS Office applications."),
    )
    drc_url = models.URLField(
        _("DRC URL"),
        help_text=_(
            "URL reference to the source document in the Documents API. May "
            "include the 'versie' querystring parameter."
        ),
        max_length=1000,
    )
    filename = models.CharField(
        _("Filename"),
        max_length=255,
        help_text=_("Filename of object on DRC API."),
        default="",
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
    original_document = PrivateMediaFileField(
        _("original document file"),
        help_text=_(
            "The original document is used to check if the document is edited before updating the document on the Documenten API."
        ),
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
    objects = DeleteQuerySet.as_manager()

    class Meta:
        verbose_name = _("Document file")
        verbose_name_plural = _("Document files")
        constraints = (
            models.UniqueConstraint(
                fields=("drc_url",),
                condition=models.Q(purpose=DocFileTypes.edit),
                name="unique_edit_drc_url",
            ),
        )

    def __str__(self):
        if not self.pk:
            return "Pending creation"

        return self.drc_url

    def delete(self):
        """
        If a document was requested for read only or is marked safe for deletion,
        delete the instance.

        Otherwise, send out a warning and protect the instance from being deleted
        as the relevant object in the DRC is still locked.
        """
        if self.safe_for_deletion or self.purpose == DocFileTypes.read:
            super().delete()

        else:
            logger.warning(
                "Object: DocumentFile {_uuid} has not been marked for deletion and has locked {drc_url} with lock {lock}.".format(
                    _uuid=self.uuid, drc_url=self.drc_url, lock=self.lock
                ),
            )

    def force_delete(self):
        """
        If one needs/wants to force delete an object,
        this makes sure the object is unlocked in the DRC.
        """
        if self.purpose == DocFileTypes.edit:
            self.unlock_drc_document()

        self.delete()

    def get_drc_document(self):
        """
        Creates a temporary ContentFile from document data from DRC API.
        """
        document = get_document(self.drc_url)
        content = get_document_content(document.inhoud)
        temp_doc = ContentFile(content, name=document.bestandsnaam)
        return temp_doc

    def unlock_drc_document(self):
        """
        This unlocks the documents and marks it safe for deletion.
        """
        unlock_document(self.drc_url, self.lock)
        self.safe_for_deletion = True
        self.save()

    def update_drc_document(self):
        """
        Checks against the local original of the document to see if the
        document was changed.

        If it was changed - push changes to DRC API and afterwards unlock document.
        Otherwise, just unlock the document.
        """
        # Get original document
        with self.original_document.storage.open(
            self.original_document.name
        ) as ori_doc:
            original_content = ori_doc.read()
            original_document = ContentFile(original_content, name=self.filename)

        # Get new document
        with self.document.storage.open(self.document.name) as edi_doc:
            edited_content = edi_doc.read()
            edited_document = ContentFile(edited_content, name=self.filename)

        # Check for any changes in size or content
        size_change = original_document.size != edited_document.size
        content_change = original_content != edited_content

        if any([size_change, content_change]):
            data = {
                "auteur": self.user.username,
                "bestandsomvang": edited_document.size,
                "bestandsnaam": self.filename,
                "inhoud": base64.b64encode(edited_content).decode("utf-8"),
                "lock": self.lock,
            }

            # Update document
            update_document(self.drc_url, data)

    def save(self, **kwargs):
        """
        Before a documentfile is saved, get the documents from the DRC API and
        store them in the relevant fields. If necessary, this also locks the
        relevant object in the DRC API.
        """
        if not self.pk:
            # Lock document in DRC API if purpose is to edit
            if self.purpose == DocFileTypes.edit:
                self.lock = lock_document(self.drc_url)

            # Get document data from DRC
            drc_doc = self.get_drc_document()
            self.filename = drc_doc.name

            # Save it to document and original document fields
            self.document = drc_doc
            self.original_document = drc_doc

        super().save(**kwargs)


@receiver(post_delete, sender=DocumentFile)
def delete_associated_files(sender, instance, **kwargs):
    """
    After an instance has been deleted it's possible that the files
    that were created by the instance creation are not deleted.

    This signal makes sure that those files are indeed deleted on singular
    deletes as well as batch deletes.
    """
    instance.original_document.storage.delete(instance.original_document.name)
    instance.document.storage.delete(instance.document.name)
