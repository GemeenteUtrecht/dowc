# Generated by Django 3.2.12 on 2022-07-18 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_documentlock"),
    ]

    operations = [
        migrations.CreateModel(
            name="CoreConfig",
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
                    "webdav_adfs_authentication",
                    models.BooleanField(
                        default=True,
                        help_text="A flag that allows webdav adfs user authentication to be switched on or off.",
                        verbose_name="Enable WebDAV ADFS user authentication",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
