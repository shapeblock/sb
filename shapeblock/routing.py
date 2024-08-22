from django.urls import path
from shapeblock.apps.consumers import AppStatusConsumer, PodLogConsumer
from shapeblock.deployments.consumers import DeployLogsConsumer

websocket_urlpatterns = [
    path("ws/apps/", AppStatusConsumer.as_asgi()),
    path("ws/deployments/<uuid:uuid>/logs/", DeployLogsConsumer.as_asgi()),
    path("ws/pod-logs/<str:app_uuid>/", PodLogConsumer.as_asgi()),
]
