from django.contrib import admin
from .models import Deployment

@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ["created_at", "app", "project", "type", "status"]

    ordering = ("-created_at",)

    def project(self, obj):
        return obj.app.project
