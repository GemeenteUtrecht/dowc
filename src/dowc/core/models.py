import base64
import logging
import os
import uuid
from typing import Optional

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext_lazy as _

from privates.fields import PrivateMediaFileField
from zgw_consumers.api_models.documenten import Document

from dowc.accounts.models import User
from dowc.core.utils import (
    get_document,
    get_document_content,
    lock_document,
    unlock_document,
    update_document,
)

from .constants import DocFileTypes, ResourceSubFolders
from .managers import DowcQuerySet

logger = logging.getLogger(__name__)


def get_parent_folder(instance, subfolder):
    return os.path.join(instance.user.username, subfolder)


def get_user_filepath_protected(instance, filename):
    parent_folder = get_parent_folder(instance, ResourceSubFolders.protected)
    return os.path.join(parent_folder, filename)


def get_user_filepath_public(instance, filename):
    parent_folder = get_parent_folder(instance, ResourceSubFolders.public)
    return os.path.join(parent_folder, filename)


class DocumentFile(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text=_("A unique UUID for the DocumentFile object."),
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
        upload_to=get_user_filepath_public,
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
        upload_to=get_user_filepath_protected,
    )
    purpose = models.CharField(
        max_length=5,
        choices=DocFileTypes.choices,
        default=DocFileTypes.read,
        help_text=_("Purpose of requesting the document."),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, help_text=_("User requesting the document.")
    )
    objects = DowcQuerySet.as_manager()
    changed_name = models.BooleanField(
        default=False,
        help_text=_("Flags a name change for updating the document on the DRC."),
    )
    info_url = models.URLField(
        default="", help_text=_("Points to the origin of the document's usage.")
    )

    api_document: Optional[Document] = None

    class Meta:
        verbose_name = _("Document file")
        verbose_name_plural = _("Document files")
        constraints = (
            models.UniqueConstraint(
                fields=("drc_url",),
                condition=models.Q(purpose=DocFileTypes.write),
                name="unique_write_drc_url",
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
        if self.purpose == DocFileTypes.write:
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
        self.api_document = unlock_document(self.drc_url, self.lock)
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

        # Check for any changes in size, content or name
        size_change = original_document.size != edited_document.size
        content_change = original_content != edited_content

        if any([size_change, content_change, self.changed_name]):
            data = {
                "auteur": self.user.username,
                "bestandsomvang": edited_document.size,
                "bestandsnaam": self.filename,
                "inhoud": base64.b64encode(edited_content).decode("utf-8"),
                "lock": self.lock,
            }

            # Update document
            return update_document(self.drc_url, data)

    # @rollback_file_creation(logger)
    def save(self, **kwargs):
        """
        Before a documentfile is saved, get the documents from the DRC API and
        store them in the relevant fields. If necessary, this also locks the
        relevant object in the DRC API.
        """
        if not self.pk:
            # Lock document in DRC API if purpose is to write
            if self.purpose == DocFileTypes.write:
                self.lock = lock_document(self.drc_url)

            drc_doc = self.get_drc_document()
            self.filename = drc_doc.name

            # Save it to document...
            self.document = drc_doc

            # ... and original document fields.
            if self.purpose == DocFileTypes.write:
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
    delete_files(instance)


def delete_files(instance):
    """
    Deletes files from a DocumentFile instance
    """
    assert type(instance) == DocumentFile

    storage = instance.document.storage
    name = instance.document.name

    if name:
        if storage.exists(name):
            storage.delete(name)

    original_storage = instance.original_document.storage
    original_name = instance.original_document.name

    if original_name:
        if original_storage.exists(original_name):
            original_storage.delete(original_name)


def rollback_file_creation(logger):
    """
    On failed saves we don't want to deal with garbage data hanging around.
    This ensures we delete those files in case.
    """

    def rollback_file_creation_inner(save):
        @functools.wraps(save)
        def wrapper(instance, **kwargs):
            assert type(instance) == DocumentFile

            try:
                return save(instance, **kwargs)

            except:
                messages = [
                    "Something went wrong with saving the documentfile object. Please contact an administrator."
                ]
                logger.error(
                    messages[0],
                    exc_info=True,
                )

                if instance.lock:
                    try:
                        unlock_document(instance.drc_url, instance.lock)

                    except:
                        messages.append(
                            f"Unlocking document failed. Document: {instance.drc_url} is still locked with lock: {instance.lock}."
                        )
                        logger.error(
                            messages[1],
                            exc_info=True,
                        )

                delete_files(instance)

                raise APIException("\n".join(messages))

        return wrapper

    return rollback_file_creation_inner
