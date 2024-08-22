import uuid

from django.db import models
from django.utils.text import slugify


from shapeblock.utils.models import BaseModel, OwnedModel


class Project(BaseModel, OwnedModel):
    name = models.CharField(null=False, max_length=150, unique=True)
    display_name = models.CharField(null=False, max_length=150)
    description = models.TextField(null=True, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)

    def __str__(self):
        return f"{self.display_name}"

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = slugify(self.display_name)
        super(Project, self).save(*args, **kwargs)
