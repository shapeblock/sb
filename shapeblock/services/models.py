import uuid

from django.db import models
from django.urls import reverse
from django.core.validators import RegexValidator

from shapeblock.utils.models import BaseModel, OwnedModel
from shapeblock.projects.models import Project
from shapeblock.apps.models import App

ServiceNameValidator = RegexValidator(
    r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
    "Only alphanumeric characters and - are allowed.",
)


class Service(BaseModel, OwnedModel):
    name = models.CharField(
        null=False, max_length=50, validators=[ServiceNameValidator]
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    STATUS_CHOICES = (
        ("starting", "Starting"),
        ("ready", "Ready"),
        ("deleted", "Deleted"),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="starting")

    SERVICE_CHOICES = (
        ("mysql", "MySQL"),
        ("postgres", "Postgres"),
        ("mongodb", "MongoDB"),
        # ("opensearch", "Opensearch"),
        ("redis", "Redis"),
        # ("rabbitmq", "RabbitMQ"),
    )
    type = models.CharField(max_length=20, null=False, choices=SERVICE_CHOICES)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="services",
    )

    # TODO: should we add version
    # version is dependent on stack

    apps = models.ManyToManyField(App, through="AppService", related_name="services")

    def __str__(self):
        return self.name

    @property
    def service_statefulset(self):
        if self.type == "postgres":
            return f"{self.name}-postgresql"
        if self.type == "mongodb":
            return f"{self.name}-mongodb"
        if self.type == "mysql":
            return f"{self.name}-mysql"
        if self.type == "redis":
            return f"{self.name}-redis-master"


class AppService(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="service")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    EXPOSED_AS_CHOICES = (
        ("separate_variables", "Separate Variables"),
        ("url", "URL"),
    )
    exposed_as = models.CharField(max_length=20, choices=EXPOSED_AS_CHOICES)

    class Meta:
        unique_together = ("app", "service")
