from rest_framework import serializers

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["display_name", "uuid", "description", "user"]

    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    def __init__(self, *args, **kwargs):
        super(ProjectSerializer, self).__init__(*args, **kwargs)
        request = self.context.get("request")

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def validate_display_name(self, value):
        if Project.objects.filter(display_name=value).exists():
            raise serializers.ValidationError(
                f"A project with the name '{value}' already exists."
            )
        return value


class ProjectReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["created_at", "display_name", "uuid", "description", "user"]

    user = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )


class ProjectRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["display_name", "uuid"]
