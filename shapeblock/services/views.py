import logging
import json

from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import get_object_or_404

from .models import Service, AppService
from shapeblock.apps.models import App
from shapeblock.apps.utils import create_env_vars, delete_env_vars
from .serializers import ServiceSerializer, ServiceReadSerializer

from .kubernetes import create_service, delete_service

from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger("django")


class ServiceViewSet(viewsets.GenericViewSet):
    """
    A viewset that provides `create`, `retrieve`, and `delete` actions for all services.
    """

    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Service.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer_class = self.serializer_class
        serializer = serializer_class(data=request.data, context={"request": request})
        if serializer.is_valid():
            service = serializer.save(user=self.request.user)
            create_service(service)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        services = Service.objects.filter(user=request.user)
        serializer = ServiceReadSerializer(services, many=True)
        return Response(serializer.data)

    def retrieve(self, request, uuid=None, *args, **kwargs):
        try:
            service = Service.objects.get(user=request.user, uuid=uuid)
        except Service.DoesNotExist:
            return Response({"detail": "Not Found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ServiceReadSerializer(service)
        return Response(serializer.data)

    def destroy(self, request, uuid=None, *args, **kwargs):
        service = self.get_queryset().get(uuid=uuid)
        delete_service(service)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AttachAppView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, uuid):
        try:
            app_uuid = request.data.get("app_uuid")
            if not app_uuid:
                return Response({"error": "App UUID is required"}, status=400)
            # TODO: validate exposed_as
            exposed_as = request.data.get("exposed_as")

            service = get_object_or_404(Service, uuid=uuid)
            app = get_object_or_404(App, uuid=app_uuid)
            app_service, created = AppService.objects.get_or_create(
                app=app,
                service=service,
                exposed_as=exposed_as,
            )
            create_env_vars(app_service)
            if not created:
                return Response(
                    {"message": "AppService association already exists"}, status=409
                )

            return Response({"status": "AppService created successfully"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class DetachAppView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, uuid):
        try:
            service = get_object_or_404(Service, uuid=uuid)

            # Retrieve the app UUID from the payload and validate it
            app_uuid = request.data.get("app_uuid")
            if not app_uuid:
                return Response({"error": "App UUID is required"}, status=400)

            app = get_object_or_404(App, uuid=app_uuid)

            # Attempt to find and delete the AppService instance
            app_service = get_object_or_404(AppService, app=app, service=service)
            delete_env_vars(app_service)
            app_service.delete()

            return Response({"status": "AppService deleted successfully"}, status=200)
        except ValueError:
            # Handle cases where UUID is malformed
            return Response({"error": "Invalid UUID provided"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def get(self, request, uuid):
        try:
            service = get_object_or_404(Service, uuid=uuid)
            app_uuid = request.data.get("app_uuid")
            if not app_uuid:
                return Response({"error": "App UUID is required"}, status=400)

            app = get_object_or_404(App, uuid=app_uuid)

            # Attempt to find and delete the AppService instance
            app_service = get_object_or_404(AppService, app=app, service=service)
            app_service = list_env_vars(app_service)
            return Response({"env_vars": app_service}, status=status.HTTP_200_OK)

        except ValueError:
            # Handle cases where UUID is malformed
            return Response({"error": "Invalid UUID provided"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def delete_env_vars(self, request, uuid):
        try:
            app_uuid = request.data.get("app_uuid")
            if not app_uuid:
                return Response({"error": "App UUID is required"}, status=400)

            service = get_object_or_404(Service, uuid=uuid)
            app = get_object_or_404(App, uuid=app_uuid)
            app_service = get_object_or_404(AppService, app=app, service=service)
            deleted_count = delete_env_vars_util(app_service)

            return Response({"delete": delete_count}, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Invalid UUID provided"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class UpdateServiceDeploymentView(View):
    def post(self, request, **kwargs):
        decoded_body = request.body.decode("utf-8")
        data = json.loads(decoded_body)
        logger.debug(decoded_body)
        service = Service.objects.get(uuid=data["service_uuid"])
        if service.status == "ready":
            # Don't update the status if service is running.
            return JsonResponse(
                {},
                status=202,
            )
        status = data.get("status")
        if status == "success":
            service.status = "ready"
            service.save()
            return JsonResponse(
                {},
                status=200,
            )
