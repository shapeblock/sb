import uuid
from django.db import models

from shapeblock.utils.models import OwnedModel

from shapeblock.apps.models import App


class Deployment(OwnedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="deployments")
    STATUS_CHOICES = (
        ("success", "Success"),
        ("running", "Running"),
        ("failed", "Failed"),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="running")
    log = models.TextField(blank=True, null=True)
    ref = models.CharField(null=True, max_length=256, blank=True)
    params = models.JSONField(null=True, blank=True)
    TYPE_CHOICES = (
        ("code", "Code Change"),
        ("config", "Config Change"),
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="code")
    pod = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"For {self.app.name}, on {self.created_at.strftime('%d-%m-%Y, %H:%M')}"
