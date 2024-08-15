from rest_framework import serializers

from .models import App, EnvVar, Secret, BuildVar, Volume,CustomDomain, InitProcess, WorkerProcess
from shapeblock.projects.models import Project
from shapeblock.services.models import Service

class ServiceRefSerializer(serializers.ModelSerializer):

    class Meta:
        model = Service
        fields = ['uuid', 'name', 'type']

class CustomDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model=CustomDomain
        fields=['id','domain']


class AppSerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = ["project", "uuid", "name", "stack", "repo", "ref","status","sub_path","user"]

    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

    project = serializers.PrimaryKeyRelatedField(
      queryset=Project.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super(AppSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')

        if request and hasattr(request, "user"):
            self.fields['project'].queryset = Project.objects.filter(user=request.user)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class InitProcessSerializer(serializers.Serializer):
    pass

class EnvVarSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvVar
        fields = ['id', 'key', 'value', 'service']

    service = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )


class SecretSerializer(serializers.ModelSerializer):
    class Meta:
        model = Secret
        fields = ['id', 'key', 'value']

class BuildVarSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuildVar
        fields = ['id', 'key', 'value']

class VolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = ['id', 'name', 'mount_path', 'size']

class InitProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = InitProcess
        fields = ['id', 'key', 'memory', 'cpu']

class WorkerProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerProcess
        fields = ['id', 'key', 'memory', 'cpu']

class ProjectReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['display_name', 'uuid']


class AppReadSerializer(serializers.ModelSerializer):

    domain = serializers.SerializerMethodField()

    class Meta:
        model = App
        fields = ["project", "uuid", "name", "stack", "repo", "ref", "sub_path", "user", "env_vars", "build_vars", "volumes", "created_at", "status", "domain", "secrets", "services", "custom_domains"]

    project = ProjectReadSerializer(required=True)

    env_vars = EnvVarSerializer(many=True)

    build_vars = BuildVarSerializer(many=True)

    volumes = VolumeSerializer(many=True)

    secrets = SecretSerializer(many=True)

    services = ServiceRefSerializer(many=True)

    custom_domains = CustomDomainSerializer(many=True)

    def get_domain(self, obj):
        return obj.domain

class AppRefSerializer(serializers.ModelSerializer):

    class Meta:
        model = App
        fields = ["uuid", "name"]
