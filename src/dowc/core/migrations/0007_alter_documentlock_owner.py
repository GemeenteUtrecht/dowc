# Generated by Django 3.2.12 on 2022-07-18 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_coreconfig"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documentlock",
            name="owner",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
