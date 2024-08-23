import logging
from github import Github, GithubException, UnknownObjectException
from django.core.exceptions import ValidationError
from django.conf import settings
from urllib.parse import urlparse
from rest_framework import serializers

from .models import (
    App,
    EnvVar,
    Secret,
    BuildVar,
    Volume,
    CustomDomain,
    InitProcess,
    WorkerProcess,
)
from shapeblock.projects.models import Project
from shapeblock.services.models import Service

logger = logging.getLogger("django")


def extract_github_org_repo(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc != "github.com":
        raise ValidationError("Invalid GitHub URL.")

    if parsed_url.scheme in ["http", "https"]:
        # HTTPS format: https://github.com/org/repo.git
        path_parts = parsed_url.path.strip("/").split("/")
    elif parsed_url.scheme == "" and parsed_url.netloc == "":
        # SSH format: git@github.com:org/repo.git
        path_parts = url.split(":")[-1].strip("/").split("/")
    else:
        raise ValidationError("Invalid GitHub URL format.")

    if len(path_parts) != 2:
        raise ValidationError("Invalid GitHub URL format.")

    org_name, repo_name = path_parts
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    return f"{org_name}/{repo_name}"


def validate_github_repo_and_branch(url, branch, user_github_token):
    repo_path = extract_github_org_repo(url)
    if user_github_token:
        gh = Github(user_github_token)
    else:
        gh = Github(
            settings.GITHUB_TOKEN
        )  # Fallback to settings token for public repos only

    try:
        logger.info(repo_path)
        try:
            repo = gh.get_repo(repo_path)
        except UnknownObjectException:
            if not user_github_token:
                raise ValidationError(
                    "A personal GitHub token is required to access private repositories."
                )
            else:
                raise ValidationError(f"The repo {url} could not be found.")

        if branch not in [b.name for b in repo.get_branches()]:
            raise ValidationError(
                f'The branch "{branch}" does not exist in the repository.'
            )
        if repo.private:
            transformed_url = f"git@github.com:{repo_path}.git"
        else:
            transformed_url = f"https://github.com/{repo_path}.git"

        return transformed_url

    except GithubException as e:
        raise ValidationError(f"GitHub API Error: {str(e)}")

    except Exception as e:
        raise ValidationError(f"An error occurred: {str(e)}")


class ServiceRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["uuid", "name", "type"]


class CustomDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomDomain
        fields = ["id", "domain"]


class AppSerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = [
            "project",
            "uuid",
            "name",
            "stack",
            "repo",
            "ref",
            "status",
            "sub_path",
            "user",
        ]

    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super(AppSerializer, self).__init__(*args, **kwargs)
        request = self.context.get("request")

        if request and hasattr(request, "user"):
            self.fields["project"].queryset = Project.objects.filter(user=request.user)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def validate(self, attrs):
        name = attrs.get("name")
        project = attrs.get("project")

        # Check for uniqueness manually
        if App.objects.filter(name=name, project=project).exists():
            raise serializers.ValidationError(
                f"An app with the name {name} already exists in project {project}."
            )

        repo = attrs.get("repo")
        ref = attrs.get("ref")
        user_github_token = self.context["request"].user.github_token
        transformed_url = validate_github_repo_and_branch(repo, ref, user_github_token)
        attrs["repo"] = transformed_url

        return attrs


class InitProcessSerializer(serializers.Serializer):
    pass


class EnvVarSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvVar
        fields = ["id", "key", "value", "service"]

    service = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )


class SecretSerializer(serializers.ModelSerializer):
    class Meta:
        model = Secret
        fields = ["id", "key", "value"]


class BuildVarSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuildVar
        fields = ["id", "key", "value"]


class VolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = ["id", "name", "mount_path", "size"]


class InitProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = InitProcess
        fields = ["id", "key"]


class WorkerProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerProcess
        fields = ["id", "key", "memory", "cpu"]


class ProjectReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["display_name", "uuid"]


class AppReadSerializer(serializers.ModelSerializer):
    domain = serializers.SerializerMethodField()

    class Meta:
        model = App
        fields = [
            "project",
            "uuid",
            "name",
            "stack",
            "repo",
            "ref",
            "sub_path",
            "user",
            "env_vars",
            "build_vars",
            "volumes",
            "created_at",
            "status",
            "domain",
            "secrets",
            "services",
            "custom_domains",
            "init_processes",
            "workers",
            "has_liveness_probe",
            "replicas",
            "autodeploy",
        ]

    project = ProjectReadSerializer(required=True)

    env_vars = EnvVarSerializer(many=True)

    build_vars = BuildVarSerializer(many=True)

    volumes = VolumeSerializer(many=True)

    secrets = SecretSerializer(many=True)

    services = ServiceRefSerializer(many=True)

    custom_domains = CustomDomainSerializer(many=True)

    init_processes = InitProcessSerializer(many=True)

    workers = WorkerProcessSerializer(many=True)

    def get_domain(self, obj):
        return obj.domain


class AppRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = ["uuid", "name"]
