import uuid
import re
from typing import Dict

from django.db import models
from django.urls import reverse
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.conf import settings
from github.GithubException import UnknownObjectException
from .mapper.validator import validate_yaml
from .git import github
from shapeblock.utils.models import BaseModel, OwnedModel
from shapeblock.projects.models import Project
from .git import GIT_REGEX

from fernet_fields import EncryptedCharField


class SBYmlNotFound(Exception):
    pass

class ServiceQuotaExceededException(Exception):
    pass

class InvalidSBYml(Exception):
    def __init__(self, errors):
        self.errors = errors


AppNameValidator = RegexValidator(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", "Only alphanumeric characters and - are allowed.")


class App(BaseModel, OwnedModel):
    name = models.CharField(null=False, max_length=50, validators=[AppNameValidator])
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    status = models.CharField(max_length=50, null=True, blank=True)

    STATUS_CHOICES = (
        ("created", "Created"),
        ("building", "Building"),
        ("ready", "Ready"),
        ("deleted", "Deleted"),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="created")

    STACK_CHOICES = (
        ("php", "PHP"),
        ("java", "Java"),
        ("python", "Python"),
        ("node", "Node.js"),
        ("ruby", "Ruby"),
        ("go", "Golang"),
        ("nginx", "Nginx"),
    )
    stack = models.CharField(max_length=20, null=False, choices=STACK_CHOICES)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="apps",
    )

    repo = models.CharField(null=False, max_length=256)
    ref = models.CharField(null=False, default="main", max_length=256)
    sub_path = models.CharField(null=True, blank=True, max_length=256)
    # TODO: should we add version
    # version is dependent on stack

    sb_yml = models.JSONField(blank=True)

    key_config = models.JSONField(blank=True, null=True)

    autodeploy = models.BooleanField(default=False)

    webhook_id = models.BigIntegerField(null=True)

    has_liveness_probe = models.BooleanField(default=True)

    replicas = models.PositiveSmallIntegerField(default=1, validators=[MaxValueValidator(6)], null=False)

    def __str__(self):
        return self.name

    @property
    def is_private(self):
        return self.repo.startswith("git@")

    @property
    def domain(self):
        return f"https://{self.project.name}-{self.name}.{settings.CLUSTER_DOMAIN}"


    def get_repo_details(self):
        match = re.match(GIT_REGEX, self.repo).groupdict()
        full_name = f"{match['org']}/{match['repo']}"
        protocol = match["protocol"]
        return protocol, full_name

    def get_user_github_token(self, user=None):
        user = user if user else self.user
        if user.github_token:
            return user.github_token
        return None

    def get_sb_yml(self) -> Dict:
        """
        Fetch the file `.sb.yml` or `.sb.yaml` from the top level folder in the git repo.
        Shapeblock won't build your app if this file isn't present.
        """
        _, repo_fullname = self.get_repo_details()

        # fetch token
        token = self.get_user_github_token()

        # bail out if no token is present
        if not token:
            if self.is_private:
                raise Exception(f"No token found for {self.name}.")
            token = settings.GITHUB_TOKEN
        repo = github.get_repo(token, repo_fullname)
        try:
            if self.sub_path:
                filename = f"{self.sub_path}/.sb.yml"
            else:
                filename = ".sb.yml"
            sb_yml = repo.get_contents(filename, ref=self.ref)
        except UnknownObjectException:
            try:
                if self.sub_path:
                    filename = f"{self.sub_path}/.sb.yaml"
                else:
                    filename = ".sb.yaml"
                sb_yml = repo.get_contents(filename, ref=self.ref)
            except UnknownObjectException:
                # TODO: log saying that sb.yml not found
                return {}
        # TODO: add gitlab support
        sb_yml_str = sb_yml.decoded_content.decode("utf-8")
        sb_yml_dict, validation_errors = validate_yaml(sb_yml_str)
        if not sb_yml_dict:
            raise InvalidSBYml(validation_errors)
        return sb_yml_dict

    def save(self, *args, **kwargs):
        if not self.sb_yml:
            # get sb yml config merge with config
            sb_yml_config = self.get_sb_yml()
            self.sb_yml = sb_yml_config
        super().save(*args, **kwargs)


EnvVarNameValidator = RegexValidator(
    r"^[A-Za-z0-9]([_A-Za-z0-9]*[A-Za-z0-9])?$", "Only alphanumeric characters and _ are allowed."
)

DomainNameValidator = RegexValidator(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$", "Please give a valid domain name."
)

class EnvVar(models.Model):
    key = models.CharField(null=False, max_length=100, validators=[EnvVarNameValidator])
    value = models.CharField(null=False, max_length=200)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='env_vars')
    service = models.ForeignKey("services.Service", on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('key', 'app')

    def __str__(self):
        return f"{self.key}-{self.app}"


class Secret(models.Model):
    key = models.CharField(null=False, max_length=100, validators=[EnvVarNameValidator])
    value = EncryptedCharField(null=False, max_length=200)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='secrets')

    class Meta:
        unique_together = ('key', 'app')

    def __str__(self):
        return f"{self.key}-{self.app}"


class BuildVar(models.Model):
    key = models.CharField(null=False, max_length=100, validators=[EnvVarNameValidator])
    value = models.CharField(null=False, max_length=200)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='build_vars')
    class Meta:
        unique_together = ('key', 'app')

    def __str__(self):
        return f"{self.key}-{self.app}"


class InitProcess(models.Model):
    key = models.CharField(null=False, max_length=100, validators=[AppNameValidator])
    memory = models.CharField(null=False, max_length=5, default="512Mi")
    cpu = models.CharField(null=False, max_length=5, default="500m")
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='init_processes')

    def __str__(self):
        return f"{self.key}-{self.app}"

    class Meta:
        unique_together = (("key", "app"),)


class WorkerProcess(models.Model):
    key = models.CharField(null=False, max_length=100, validators=[AppNameValidator])
    #TODO: add a memory and CPU validator
    memory = models.CharField(null=False, max_length=5, default="1Gi")
    cpu = models.CharField(null=False, max_length=5, default="1000m")
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='workers')

    def __str__(self):
        return f"{self.key}-{self.app}"

    class Meta:
        unique_together = (("key", "app"),)


class Volume(models.Model):
    name = models.CharField(null=False, max_length=100, validators=[AppNameValidator])
    mount_path = models.CharField(
        max_length=1024,
        validators=[RegexValidator(regex=r"^/workspace/.+", message="Path must start with /workspace")],
    )
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='volumes')
    size = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=2, null=False)

    class Meta:
        unique_together = ("name", "mount_path","size","app")

    def __str__(self):
        return self.name


class CustomDomain(models.Model):
    domain = models.CharField(null=False, max_length=100, validators=[DomainNameValidator])
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='custom_domains')

    class Meta:
        unique_together = ('domain', 'app')

    def __str__(self):
        return f"{self.domain}-{self.app}"
