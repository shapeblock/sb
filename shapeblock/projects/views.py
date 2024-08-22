import logging

from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Project
from .serializers import ProjectSerializer, ProjectReadSerializer
from rest_framework.permissions import IsAuthenticated
from .kubernetes import run_setup_project, run_delete_project
from rest_framework.decorators import action
from shapeblock.services.serializers import ServiceSerializer
from rest_framework.views import APIView
from shapeblock.apps.models import App
from shapeblock.apps.serializers import AppRefSerializer
from shapeblock.services.models import Service
from shapeblock.services.serializers import ServiceRefSerializer

logger = logging.getLogger("django")


class ProjectViewSet(viewsets.GenericViewSet):
    """
    A viewset that provides `create`, `retrieve`, and `delete` actions for all provider types.
    """

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

    def get_queryset(self):
        return Project.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data, context={"request": request})
        if serializer.is_valid():
            project = serializer.save(user=self.request.user)
            run_setup_project(project)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="services")
    def services(self, request, uuid=None):
        project = self.get_object()
        services = project.services.all()
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        projects = Project.objects.filter(user=request.user)
        serializer = ProjectReadSerializer(projects, many=True)
        return Response(serializer.data)

    def retrieve(self, request, uuid=None, *args, **kwargs):
        project = Project.objects.get(uuid=uuid, user=request.user)
        serializer = ProjectReadSerializer(project)
        return Response(serializer.data)

    def destroy(self, request, uuid=None, *args, **kwargs):
        project = Project.objects.get(uuid=uuid, user=request.user)
        run_delete_project(project)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectAppsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        try:
            project = Project.objects.get(uuid=uuid, user=request.user)
        except Project.DoesNotExist:
            return Response({"detail": "Project not found."}, status=404)
        apps = App.objects.filter(project=project)

        serializer = AppRefSerializer(apps, many=True)

        # Return the serialized data
        return Response(serializer.data)


class ProjectServicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        try:
            project = Project.objects.get(uuid=uuid, user=request.user)
        except Project.DoesNotExist:
            return Response({"detail": "Project not found."}, status=404)
        services = Service.objects.filter(project=project)

        serializer = ServiceRefSerializer(services, many=True)

        # Return the serialized data
        return Response(serializer.data)
