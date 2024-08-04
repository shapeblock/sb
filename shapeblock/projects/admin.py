from django.contrib import admin

# Register your models here.
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = (
        "name",
    )
    ordering = ("-created_at",)

    list_display = ["created_at", "name", "user"]
