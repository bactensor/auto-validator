# Generated by Django 4.2.16 on 2024-09-19 02:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_rename_maintainers_id_subnet_maintainers_ids"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subnet",
            name="hw_requirements",
            field=models.TextField(blank=True, max_length=4095, null=True),
        ),
    ]
