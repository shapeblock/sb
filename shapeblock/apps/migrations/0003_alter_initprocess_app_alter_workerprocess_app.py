# Generated by Django 5.0.6 on 2024-08-15 12:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='initprocess',
            name='app',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='init_processes', to='apps.app'),
        ),
        migrations.AlterField(
            model_name='workerprocess',
            name='app',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workers', to='apps.app'),
        ),
    ]
