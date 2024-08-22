from rest_framework import serializers

from .models import Service
from shapeblock.projects.models import Project
from shapeblock.projects.serializers import ProjectRefSerializer
from shapeblock.apps.serializers import AppRefSerializer


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["project", "uuid", "name", "type", "user"]

    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super(ServiceSerializer, self).__init__(*args, **kwargs)
        request = self.context.get("request")

        if request and hasattr(request, "user"):
            self.fields["project"].queryset = Project.objects.filter(user=request.user)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ServiceReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "created_at",
            "project",
            "uuid",
            "name",
            "type",
            "user",
            "apps",
            "status",
        ]

    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    project = ProjectRefSerializer(required=True)

    apps = AppRefSerializer(many=True, required=False)


class ServiceRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["uuid", "name", "type"]
