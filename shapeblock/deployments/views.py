import logging
import json
import base64

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from rest_framework.generics import ListCreateAPIView
from .models import Deployment, App
from .serializers import DeploymentSerializer, DeploymentReadSerializer
from shapeblock.apps.kubernetes import run_deploy_pipeline
from shapeblock.apps.utils import get_kubeconfig

logger = logging.getLogger("django")


class DeploymentListCreateAPIView(ListCreateAPIView):
    serializer_class = DeploymentSerializer

    def get_queryset(self):
        """
        This view should return a list of all the Deployments
        for the currently specified app by filtering against `app_id` in the URL.
        """
        app_id = self.kwargs["app_uuid"]
        app = get_object_or_404(App, uuid=app_id)
        return Deployment.objects.filter(app=app)

    def perform_create(self, serializer):
        """
        Create a new Deployment instance, ensuring it's associated with the specified app.
        """
        app_id = self.kwargs["app_uuid"]
        app = get_object_or_404(App, uuid=app_id)
        deployment = serializer.save(app=app)
        # TODO: check for same ref deploy
        # TODO: do a diff between previous and current deploy variables
        # TODO: check for deployment pipeline creation status
        run_deploy_pipeline(deployment)
        app.status = "building"
        app.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"uuid": serializer.instance.uuid}, status=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        deployments = self.get_queryset().order_by("-created_at")
        serializer = DeploymentReadSerializer(deployments, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name="dispatch")
class UpdateDeploymentView(View):
    def post(self, request, **kwargs):
        decoded_body = request.body.decode("utf-8")
        data = json.loads(decoded_body)
        logger.debug(decoded_body)
        deployment = Deployment.objects.get(uuid=data["deployment_uuid"])
        if deployment.status != "running":
            # Don't update the status if deployment isn't running.
            return JsonResponse(
                {},
                status=202,
            )
        pod_name = data.get("pod")
        if pod_name:
            deployment.pod = pod_name
        deployment.status = data["status"]
        if deployment.log:
            deployment.log += data["logs"]
        else:
            deployment.log = data["logs"]
        deployment.save()
        if deployment.status == "failed":
            # TODO: fetch app previous status
            deployment.app.status = "created"
            deployment.app.save()
        if deployment.status == "success":
            deployment.app.status = "ready"
            deployment.app.save()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"deployment_{deployment.uuid}",
            {
                "type": "deploy_logs",
                "data": {"log": data["logs"], "status": data["status"]},
            },
        )

        # Update websocket inf deployment is finished
        if deployment.status in ["failed", "success"]:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"apps",
                {
                    "type": "app_status_message",
                    "data": {
                        "uuid": str(deployment.app.uuid),
                        "status": deployment.app.status,
                    },
                },
            )

        return JsonResponse(
            {},
            status=200,
        )


class PodInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, deployment_uuid, *args, **kwargs):
        deployment = get_object_or_404(Deployment, uuid=deployment_uuid)
        kubeconfig = get_kubeconfig()
        kubeconfig_bytes = base64.b64encode(kubeconfig.encode("utf-8"))
        response_data = {
            "name": deployment.pod,
            "kubeconfig": kubeconfig_bytes.decode("utf-8"),
            "namespace": deployment.app.project.name,
        }
        logger.debug(response_data)
        return Response(response_data)
