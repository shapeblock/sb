# Generated by Django 5.0.6 on 2024-08-21 05:22

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('apps', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Deployment',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('success', 'Success'), ('running', 'Running'), ('failed', 'Failed')], default='running', max_length=10)),
                ('log', models.TextField(blank=True, null=True)),
                ('ref', models.CharField(blank=True, max_length=256, null=True)),
                ('params', models.JSONField(blank=True, null=True)),
                ('type', models.CharField(choices=[('code', 'Code Change'), ('config', 'Config Change')], default='code', max_length=10)),
                ('pod', models.CharField(blank=True, max_length=100, null=True)),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deployments', to='apps.app')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_author', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
