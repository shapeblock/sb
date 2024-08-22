from django.contrib import admin

from .models import App, EnvVar, Volume, BuildVar, CustomDomain


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    readonly_fields = (
        "name",
        "stack",
        "project",
        "user",
        "autodeploy",
        "webhook_id",
    )

    ordering = ("-created_at",)

    list_display = [
        "created_at",
        "name",
        "stack",
        "project",
        "user",
        "status",
        "autodeploy",
    ]


@admin.register(BuildVar)
class BuildVarAdmin(admin.ModelAdmin):
    pass


@admin.register(EnvVar)
class EnvVarAdmin(admin.ModelAdmin):
    pass


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ["name", "mount_path", "size", "app", "project"]

    def project(self, obj):
        return obj.app.project


@admin.register(CustomDomain)
class CustomDomainAdmin(admin.ModelAdmin):
    list_display = ["domain", "app"]

    def app(self, obj):
        return obj.app
