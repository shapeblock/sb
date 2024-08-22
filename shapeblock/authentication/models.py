from django.db import models
from django.contrib.auth.models import AbstractUser
from fernet_fields import EncryptedCharField


class CustomUser(AbstractUser):
    """
    Additional fields for the user
    """

    class Meta:
        db_table = "auth_user"

    github_token = EncryptedCharField(null=True, max_length=200, blank=True)
