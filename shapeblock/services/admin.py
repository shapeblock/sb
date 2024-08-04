from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    readonly_fields = (
        "name",
        "type",
        "project",
        "user",
    )

    ordering = ("-created_at",)

    list_display = ["created_at", "name", "type", "project", "cluster", "user", "status"]

    def cluster(self, obj):
        return obj.project.cluster
