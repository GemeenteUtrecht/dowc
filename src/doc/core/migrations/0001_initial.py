# Generated by Django 2.2.14 on 2020-12-23 13:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import doc.core.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentFile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="This unique UUID is used to identify the edited document in case the name of the document is changed.",
                        unique=True,
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "safe_for_deletion",
                    models.BooleanField(
                        default=False,
                        help_text="The document associated to this object has been updated on the DRC and is ready for deletion.",
                        verbose_name="Safe for deletion",
                    ),
                ),
                (
                    "document",
                    models.FileField(
                        help_text="This document can be edited directly by MS Office applications.",
                        upload_to=doc.core.models.create_new_document_path,
                        verbose_name="This document is to be edited or read.",
                    ),
                ),
                (
                    "drc_url",
                    models.URLField(
                        help_text="URL reference to the source document in the Documents API. May include the 'versie' querystring parameter.",
                        max_length=1000,
                        verbose_name="DRC URL",
                    ),
                ),
                (
                    "lock",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Lock that is provided by Documenten API when you need to edit a document.",
                        max_length=100,
                        verbose_name="lock hash",
                    ),
                ),
                (
                    "original_document",
                    models.FileField(
                        help_text="The original document is used to check if the document is edited before updating the document on the Documenten API.",
                        upload_to=doc.core.models.create_original_document_path,
                        verbose_name="original document file",
                    ),
                ),
                (
                    "purpose",
                    models.CharField(
                        choices=[("edit", "Edit"), ("read", "Read")],
                        default="read",
                        help_text="Purpose of requesting the document.",
                        max_length=4,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User requesting the document.",
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Document file",
                "verbose_name_plural": "Document files",
            },
        ),
    ]
