# Generated by Django 5.0.6 on 2024-08-21 05:22

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('apps', '0001_initial'),
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AppService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exposed_as', models.CharField(choices=[('separate_variables', 'Separate Variables'), ('url', 'URL')], max_length=20)),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service', to='apps.app')),
            ],
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=50, validators=[django.core.validators.RegexValidator('^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', 'Only alphanumeric characters and - are allowed.')])),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('starting', 'Starting'), ('ready', 'Ready'), ('deleted', 'Deleted')], default='starting', max_length=10)),
                ('type', models.CharField(choices=[('mysql', 'MySQL'), ('postgres', 'Postgres'), ('mongodb', 'MongoDB'), ('redis', 'Redis')], max_length=20)),
                ('apps', models.ManyToManyField(related_name='services', through='services.AppService', to='apps.app')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='services', to='projects.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_author', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='appservice',
            name='service',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services.service'),
        ),
        migrations.AlterUniqueTogether(
            name='appservice',
            unique_together={('app', 'service')},
        ),
    ]
