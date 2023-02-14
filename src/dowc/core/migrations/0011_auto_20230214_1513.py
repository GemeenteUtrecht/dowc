# Generated by Django 3.2.12 on 2023-02-14 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_remove_documentfile_zaak"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentfile",
            name="emailed",
            field=models.BooleanField(
                default=False,
                help_text="Flags if user already received an email about its destruction.",
            ),
        ),
        migrations.AddField(
            model_name="documentfile",
            name="error",
            field=models.BooleanField(
                default=False,
                help_text="Indicate if something went wrong. Used to not spam users with emails if something breaks in the DRC lock/unlock/update loop.",
            ),
        ),
        migrations.AddField(
            model_name="documentfile",
            name="error_msg",
            field=models.TextField(default="", help_text="Copy of the error message."),
        ),
        migrations.AddField(
            model_name="documentfile",
            name="force_deleted",
            field=models.BooleanField(
                default=False, help_text="Flags if instance was force deleted."
            ),
        ),
    ]
