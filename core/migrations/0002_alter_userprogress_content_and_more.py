# Generated by Django 5.1.6 on 2025-03-26 10:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprogress",
            name="content",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="user_progresses",
                to="core.content",
            ),
        ),
        migrations.AddConstraint(
            model_name="userprogress",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("content__isnull", False),
                    ("challenge__isnull", False),
                    _connector="OR",
                ),
                name="at_least_one_content_or_challenge",
            ),
        ),
    ]
