import logging
import base64
from .models import App,EnvVar
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import App, EnvVar, BuildVar, Secret, Volume,CustomDomain
from .serializers import AppSerializer, EnvVarSerializer, BuildVarSerializer, SecretSerializer, VolumeSerializer, AppReadSerializer,CustomDomainSerializer
from rest_framework.permissions import IsAuthenticated
from .kubernetes import delete_app_task
from .kubernetes import delete_app_task, get_app_pod
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
        serializer = serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
          serializer.save(user=self.request.user)
          return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


class KeyValAPIView(APIView):

    permission_classes = [IsAuthenticated]

    key_name = 'key'

    def get(self, request, uuid):

        try:
            app = App.objects.get(uuid=uuid, user=request.user)
        except App.DoesNotExist:
            return Response({'detail': 'App not found.'}, status=404)
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
            return Response({'detail': 'App not found.'}, status=404)

        entity_key = self.entity_key
        # Extract env_vars and delete lists from the request data
        kvs_to_update = request.data.get(entity_key, [])
        keys_to_delete = request.data.get('delete', [])

        if not kvs_to_update and not keys_to_delete:
            return Response({'detail': f"Either the \"{entity_key}\" or \"delete\" key must be present in payload."}, status=status.HTTP_400_BAD_REQUEST)
        # Validate that no key is found in both lists
        update_keys = [kv[self.key_name] for kv in kvs_to_update]
        if any(key in keys_to_delete for key in update_keys):
            return Response({'detail': 'The same key cannot be present in both update and delete lists.'}, status=status.HTTP_400_BAD_REQUEST)

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
            if kv.get('id'):
                self.model_class.objects.filter(id=kv['id']).update(value=kv['value'], app=app, key=kv['key'])
            else:
                self.model_class.objects.create(value=kv['value'], app=app, key=kv['key'])


class AppEnvVarAPIView(KeyValAPIView):

    model_class = EnvVar
    serializer_class = EnvVarSerializer
    entity_key = 'env_vars'


class AppSecretAPIView(KeyValAPIView):

    model_class = Secret
    serializer_class = SecretSerializer
    entity_key = 'secrets'


class AppBuildVarsAPIView(KeyValAPIView):

    model_class = BuildVar
    serializer_class = BuildVarSerializer
    entity_key = 'build_vars'


class InitProcessView(APIView):
    def post(self, request):
        serializer = InitProcessSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Run migrations
                call_command('migrate', interactive=False)
                return Response({'message': 'Migrations completed successfully'}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VolumesAPIView(APIView):
    model_class = Volume
    serializer_class = VolumeSerializer
    entity_key = 'volumes'
    key_name = 'name'

    def patch(self, request, uuid):

        try:
            app = App.objects.get(uuid=uuid, user=request.user)
        except App.DoesNotExist:
            return Response({'detail': 'App not found.'}, status=404)

        entity_key = self.entity_key
        # Extract env_vars and delete lists from the request data
        kvs_to_update = request.data.get(entity_key, [])
        keys_to_delete = request.data.get('delete', [])

        if not kvs_to_update and not keys_to_delete:
            return Response({'detail': f"Either the \"{entity_key}\" or \"delete\" key must be present in payload."}, status=status.HTTP_400_BAD_REQUEST)
        # Validate that no key is found in both lists
        update_names = [kv[self.key_name] for kv in kvs_to_update]
        if any(name in keys_to_delete for name in update_names):
            return Response({'detail': 'The same key cannot be present in both update and delete lists.'}, status=status.HTTP_400_BAD_REQUEST)

        model_class = self.model_class
        # Process deletions
        for name in keys_to_delete:
            model_class.objects.filter(app=app, name=name).delete()

        # Process updates and creations
        self.update(app, kvs_to_update)

        # Prepare the response
        serializer_class = self.serializer_class
        updated_vars = model_class.objects.filter(app=app)
        serializer = serializer_class(updated_vars, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, app, kvs):
        for kv in kvs:
            volume_id = kv.get('id')
            name = kv.get('name')
            mount_path = kv.get('mount_path')
            size = kv.get('size')

            if volume_id:
                self.model_class.objects.filter(id=volume_id).update(
                    mount_path=mount_path,
                    size=size,
                    app=app,
                    name=name
                )
            else:
                self.model_class.objects.create(
                    mount_path=mount_path,
                    size=size,
                    app=app,
                    name=name
                )

class CustomDomainView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, app_uuid):
        try:
            app = App.objects.get(uuid=app_uuid)
        except App.DoesNotExist:
            raise NotFound("App not found")

        custom_domains = CustomDomain.objects.filter(app=app)
        serializer = CustomDomainSerializer(custom_domains, many=True)
        return Response(serializer.data)

    def post(self, request, app_uuid):
        try:
            app = App.objects.get(uuid=app_uuid)
        except App.DoesNotExist:
            raise NotFound("App not found")

        custom_domains_data = request.data.get('custom_domains', [])
        delete_domains_data = request.data.get('delete', [])

        # Validate custom domains
        for domain_data in custom_domains_data:
            domain = domain_data.get('domain')
            if not domain:
                return Response({'error': 'Domain field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Add or update custom domains
        for domain_data in custom_domains_data:
            domain_id = domain_data.get('id')
            domain = domain_data.get('domain')
            if domain:
                if domain_id:
                    # Update existing domain
                    CustomDomain.objects.filter(id=domain_id, app=app).update(domain=domain)
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
        try:
            app = App.objects.get(uuid=app_uuid)
        except App.DoesNotExist:
            raise NotFound("App not found")

        CustomDomain.objects.filter(app=app).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)