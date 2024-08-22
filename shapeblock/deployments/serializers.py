from rest_framework import serializers

from .models import Deployment
from shapeblock.apps.models import App, EnvVar, Secret, BuildVar, Volume
from shapeblock.apps.git.common import get_commit_sha


class DeploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deployment
        fields = ["uuid", "created_at", "status", "ref", "params", "user"]

    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        app = validated_data["app"]
        # create params
        params = {
            "env_vars": self.get_env_vars(app),
            "secrets": self.get_secrets(app),
            "build_vars": self.get_build_vars(app),
            "volumes": self.get_volumes(app),
        }
        validated_data["params"] = params
        # check if previous deployment failed
        # check if params are same
        # check if last commit is same
        new_ref = get_commit_sha(app.repo, app.ref, app.user, "github")
        validated_data["ref"] = new_ref
        last_deployment = (
            Deployment.objects.filter(app=app).order_by("-created_at").first()
        )
        if last_deployment:
            conditions_met = (
                last_deployment.status == "failed"
                or not deep_dict_compare(last_deployment.params, params)
                or last_deployment.ref != new_ref
            )
        else:
            # If there is no last deployment, proceed to create a new one
            conditions_met = True

        if conditions_met:
            print(validated_data)
            # If any condition is met, create and return the new Deployment instance
            return super().create(validated_data)
        else:
            raise serializers.ValidationError(
                "Deployment conditions not met, deployment not created."
            )
        return None

    def get_env_vars(self, app):
        env_vars = EnvVar.objects.filter(app=app)
        return {env_var.key: env_var.value for env_var in env_vars}

    def get_secrets(self, app):
        secrets = Secret.objects.filter(app=app)
        return {secret.key: secret.value for secret in secrets}

    def get_build_vars(self, app):
        build_vars = BuildVar.objects.filter(app=app)
        return {build_var.key: build_var.value for build_var in build_vars}

    def get_volumes(self, app):
        volumes = Volume.objects.filter(app=app)
        return [
            {"name": volume.name, "mount_path": volume.mount_path, "size": volume.size}
            for volume in volumes
        ]


class DeploymentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deployment
        fields = ["uuid", "created_at", "status", "ref", "params", "user", "log"]

    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )


def deep_dict_compare(d1, d2):
    """
    Recursively compares two dictionaries to determine if they are equal,
    accounting for nested structures and lists.
    """
    if isinstance(d1, dict) and isinstance(d2, dict):
        if d1.keys() != d2.keys():
            return False
        for key in d1.keys():
            if not deep_dict_compare(d1[key], d2[key]):
                return False
        return True
    elif isinstance(d1, list) and isinstance(d2, list):
        if len(d1) != len(d2):
            return False
        return all(deep_dict_compare(item1, item2) for item1, item2 in zip(d1, d2))
    else:
        return d1 == d2
