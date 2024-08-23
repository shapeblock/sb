import logging
import base64
import json
from .models import App, EnvVar
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse

from .models import (
    App,
    EnvVar,
    BuildVar,
    Secret,
    Volume,
    CustomDomain,
    InitProcess,
    WorkerProcess,
)
from .serializers import (
    AppSerializer,
    EnvVarSerializer,
    BuildVarSerializer,
    SecretSerializer,
    VolumeSerializer,
    AppReadSerializer,
    CustomDomainSerializer,
    InitProcessSerializer,
    WorkerProcessSerializer,
)
from rest_framework.permissions import IsAuthenticated
from .kubernetes import delete_app_task, create_app_secret, run_deploy_pipeline
from .kubernetes import delete_app_task, get_app_pod
from .utils import (
    get_kubeconfig,
    add_github_deploy_key,
    add_github_webhook,
    trigger_deploy_from_github_webhook,
)
from shapeblock.deployments.models import Deployment

logger = logging.getLogger("django")


class AppViewSet(viewsets.GenericViewSet):
    """
    A viewset that provides `create`, `retrieve`, and `delete` actions for all provider types.
    """

    serializer_class = AppSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return App.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer_class = self.serializer_class
        serializer = serializer_class(data=request.data, context={"request": request})
        if serializer.is_valid():
            app = serializer.save(user=self.request.user)
            try:
                self.create_app_secret(app)
            except Exception as e:
                return Response(
                    "Failed to create app: {}".format(e),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create_app_secret(self, app):
        add_github_deploy_key(app)
        create_app_secret(app)

    def list(self, request, *args, **kwargs):
        apps = App.objects.filter(user=request.user)
        serializer = AppReadSerializer(apps, many=True)
        return Response(serializer.data)

    def retrieve(self, request, uuid=None, *args, **kwargs):
        app = App.objects.get(uuid=uuid, user=request.user)
        serializer = AppReadSerializer(app)
        return Response(serializer.data)

    def destroy(self, request, uuid=None, *args, **kwargs):
        app = self.get_queryset().get(uuid=uuid)
        delete_app_task(app)
        app.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AppScaleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, uuid):
        try:
            app = App.objects.get(uuid=uuid, user=request.user)
        except App.DoesNotExist:
            return Response({"detail": "App not found."}, status=404)

        if app.status == "building":
            return Response("app is building, cannot scale", status=400)

        replicas = request.data.get("replicas")
        if replicas:
            app.replicas = int(replicas)
            deployment = Deployment.objects.create(
                user=request.user,
                app=app,
                type="config",
            )
            app.status = "building"
            app.save()
            run_deploy_pipeline(deployment)
        serializer = AppReadSerializer(app)
        return Response(serializer.data)


class LivenessProbeView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, uuid):
        try:
            app = App.objects.get(uuid=uuid, user=request.user)
        except App.DoesNotExist:
            return Response({"detail": "App not found."}, status=404)

        has_liveness_probe = request.data.get("liveness_probe")
        if has_liveness_probe in ["true", "True", "1", "yes", "on", True]:
            has_liveness_probe = True
        elif has_liveness_probe in ["false", "False", "0", "no", "off", False]:
            has_liveness_probe = False
        else:
            return Response(
                "Invalid boolean value for liveness_probe",
                status=status.HTTP_400_BAD_REQUEST,
            )
        app.has_liveness_probe = has_liveness_probe
        app.save()
        serializer = AppReadSerializer(app)
        return Response(serializer.data)


class AutoDeployView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, uuid):
        try:
            app = App.objects.get(uuid=uuid, user=request.user)
        except App.DoesNotExist:
            return Response({"detail": "App not found."}, status=404)

        autodeploy = request.data.get("autodeploy")
        if autodeploy in ["true", "True", "1", "yes", "on", True]:
            token = app.get_user_github_token()
            if not token:
                return Response(
                    "Webhooks can be added only after integrating with Github",
                    status=status.HTTP_400_BAD_REQUEST,
                )
            autodeploy = True
            # TODO: make this atomic so that app save and github add happen together
            add_github_webhook(app)
        elif autodeploy in ["false", "False", "0", "no", "off", False]:
            autodeploy = False
        else:
            return Response(
                "Invalid boolean value for autodeploy",
                status=status.HTTP_400_BAD_REQUEST,
            )
        app.autodeploy = autodeploy
        app.save()
        serializer = AppReadSerializer(app)
        return Response(serializer.data)


class KeyValAPIView(APIView):
    permission_classes = [IsAuthenticated]

    key_name = "key"

    def get(self, request, uuid):
        try:
            app = App.objects.get(uuid=uuid, user=request.user)
        except App.DoesNotExist:
            return Response({"detail": "App not found."}, status=404)
        # Retrieve all k,v instances related to the app
        model_class = self.model_class
        kvs = model_class.objects.filter(app=app)

        # Serialize the queryset
        serializer_class = self.serializer_class
        serializer = serializer_class(kvs, many=True)

        # Return the serialized data
        return Response(serializer.data)

    def patch(self, request, uuid):
        try:
            app = App.objects.get(uuid=uuid, user=request.user)
        except App.DoesNotExist:
            return Response({"detail": "App not found."}, status=404)

        entity_key = self.entity_key
        # Extract env_vars and delete lists from the request data
        kvs_to_update = request.data.get(entity_key, [])
        keys_to_delete = request.data.get("delete", [])

        if not kvs_to_update and not keys_to_delete:
            return Response(
                {
                    "detail": f'Either the "{entity_key}" or "delete" key must be present in payload.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Validate that no key is found in both lists
        update_keys = [kv[self.key_name] for kv in kvs_to_update]
        if any(key in keys_to_delete for key in update_keys):
            return Response(
                {
                    "detail": "The same key cannot be present in both update and delete lists."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        model_class = self.model_class
        # Process deletions
        for key in keys_to_delete:
            model_class.objects.filter(app=app, key=key).delete()

        # Process updates and creations
        self.update(app, kvs_to_update)

        # Prepare the response
        serializer_class = self.serializer_class
        updated_vars = model_class.objects.filter(app=app)
        serializer = serializer_class(updated_vars, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, app, kvs):
        for kv in kvs:
            if kv.get("id"):
                self.model_class.objects.filter(id=kv["id"]).update(
                    value=kv["value"], app=app, key=kv["key"]
                )
            else:
                self.model_class.objects.create(
                    value=kv["value"], app=app, key=kv["key"]
                )


class AppEnvVarAPIView(KeyValAPIView):
    model_class = EnvVar
    serializer_class = EnvVarSerializer
    entity_key = "env_vars"


class AppSecretAPIView(KeyValAPIView):
    model_class = Secret
    serializer_class = SecretSerializer
    entity_key = "secrets"


class AppBuildVarsAPIView(KeyValAPIView):
    model_class = BuildVar
    serializer_class = BuildVarSerializer
    entity_key = "build_vars"


class InitProcessView(KeyValAPIView):
    model_class = InitProcess
    serializer_class = InitProcessSerializer
    entity_key = "init_processes"
    key_name = "key"

    def update(self, app, kvs):
        for kv in kvs:
            process_id = kv.get("id")
            key = kv.get("key")

            if process_id:
                self.model_class.objects.filter(id=process_id).update(
                    key=key,
                )
            else:
                self.model_class.objects.create(
                    key=key,
                    app=app,
                )


class WorkerProcessView(KeyValAPIView):
    model_class = WorkerProcess
    serializer_class = WorkerProcessSerializer
    entity_key = "workers"
    key_name = "key"

    def update(self, app, kvs):
        for kv in kvs:
            process_id = kv.get("id")
            key = kv.get("key")
            memory = kv.get("memory")
            cpu = kv.get("cpu")

            if process_id:
                worker = self.model_class.objects.filter(id=process_id)
            else:
                worker = self.model_class()
                worker.app = app
            worker.key = key
            if memory:
                worker.memory = memory
            if cpu:
                worker.cpu = cpu
            worker.save()


class VolumesAPIView(KeyValAPIView):
    model_class = Volume
    serializer_class = VolumeSerializer
    entity_key = "volumes"
    key_name = "name"

    def update(self, app, kvs):
        for kv in kvs:
            volume_id = kv.get("id")
            name = kv.get("name")
            mount_path = kv.get("mount_path")
            size = kv.get("size")

            if volume_id:
                self.model_class.objects.filter(id=volume_id).update(
                    mount_path=mount_path, size=size, app=app, name=name
                )
            else:
                self.model_class.objects.create(
                    mount_path=mount_path, size=size, app=app, name=name
                )


class ShellInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid)
        pod_name = get_app_pod(app)
        kubeconfig = get_kubeconfig()
        kubeconfig_bytes = base64.b64encode(kubeconfig.encode("utf-8"))
        response_data = {
            "name": pod_name,
            "kubeconfig": kubeconfig_bytes.decode("utf-8"),
            "namespace": app.project.name,
        }
        return Response(response_data)


class CustomDomainView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, app_uuid):
        app = get_object_or_404(App, uuid=app_uuid)
        custom_domains = CustomDomain.objects.filter(app=app)
        serializer = CustomDomainSerializer(custom_domains, many=True)
        return Response(serializer.data)

    def post(self, request, app_uuid):
        app = get_object_or_404(App, uuid=app_uuid)
        custom_domains_data = request.data.get("custom_domains", [])
        delete_domains_data = request.data.get("delete", [])

        # Validate custom domains
        for domain_data in custom_domains_data:
            domain = domain_data.get("domain")
            if not domain:
                return Response(
                    {"error": "Domain field is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Add or update custom domains
        for domain_data in custom_domains_data:
            domain_id = domain_data.get("id")
            domain = domain_data.get("domain")
            if domain:
                if domain_id:
                    # Update existing domain
                    CustomDomain.objects.filter(id=domain_id, app=app).update(
                        domain=domain
                    )
                else:
                    # Create new domain
                    CustomDomain.objects.create(app=app, domain=domain)

        # Delete custom domains
        for domain in delete_domains_data:
            CustomDomain.objects.filter(app=app, domain=domain).delete()

        # Serialize and return updated custom domains
        custom_domains = CustomDomain.objects.filter(app=app)
        serializer = CustomDomainSerializer(custom_domains, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, app_uuid):
        app = get_object_or_404(App, uuid=app_uuid)
        CustomDomain.objects.filter(app=app).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@require_POST
@csrf_exempt
def webhook_view(request):
    try:
        # Parse the incoming JSON payload
        payload = json.loads(request.body)

        delivery_id = request.headers.get("X-GitHub-Delivery")
        # Log the payload
        logger.info("Webhook received: %s", delivery_id)

        trigger_deploy_from_github_webhook(request.headers, payload)
        # Return success response
        return JsonResponse({"status": "success"})
    except json.JSONDecodeError as e:
        # Log the error
        logger.error("Invalid JSON received: %s", e)

        # Return error response
        return HttpResponse(status=400)
