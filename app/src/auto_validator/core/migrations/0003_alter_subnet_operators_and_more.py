# Generated by Django 4.2.15 on 2024-09-05 01:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_block_hotkey_operator_server_subnet_subnetslot_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subnet",
            name="operators",
            field=models.ManyToManyField(blank=True, null=True, related_name="subnets", to="core.operator"),
        ),
        migrations.AlterField(
            model_name="subnetslot",
            name="deregistration_block",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="deregistration_slots",
                to="core.block",
            ),
        ),
        migrations.AlterField(
            model_name="subnetslot",
            name="registration_block",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="registration_slots",
                to="core.block",
            ),
        ),
        migrations.AlterField(
            model_name="subnetslot",
            name="subnet",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="slots",
                to="core.subnet",
            ),
        ),
        migrations.AlterField(
            model_name="validatorinstance",
            name="hotkey",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="validator_instances",
                to="core.hotkey",
            ),
        ),
    ]
