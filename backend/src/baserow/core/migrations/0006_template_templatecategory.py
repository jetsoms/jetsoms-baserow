# Generated by Django 2.2.11 on 2021-04-04 13:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplateCategory",
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
                ("name", models.CharField(max_length=32)),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Template",
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
                ("name", models.CharField(max_length=64)),
                (
                    "slug",
                    models.SlugField(
                        help_text="The template slug that is used to match the "
                        "template with the JSON file name."
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        help_text="The font awesome class name that can be used for "
                        "displaying purposes.",
                        max_length=32,
                    ),
                ),
                (
                    "categories",
                    models.ManyToManyField(
                        related_name="templates", to="core.TemplateCategory"
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        help_text="The group containing the applications related to "
                        "the template. The read endpoints related to that "
                        "group are publicly accessible for preview "
                        "purposes.",
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        to="core.Group",
                    ),
                ),
                (
                    "export_hash",
                    models.CharField(
                        blank=True,
                        help_text="The export hash that is used to compare if the "
                        "exported group applications have changed when "
                        "syncing the templates.",
                        max_length=64,
                    ),
                ),
                (
                    "keywords",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Keywords related to the template that can be used "
                        "for search.",
                    ),
                ),
            ],
            options={
                "ordering": ("name",),
            },
        ),
    ]
