from django.urls import path
from . import views
from shapeblock.apps.views import (
    CustomDomainView,
    InitProcessView,
    WorkerProcessView,
    AutoDeployView,
    LivenessProbeView,
    AppScaleView,
)
from shapeblock.deployments.views import DeploymentListCreateAPIView

urlpatterns = [
    path(
        "",
        views.AppViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="app-list",
    ),
    path(
        "<uuid:uuid>/",
        views.AppViewSet.as_view(
            {
                "get": "retrieve",
                "delete": "destroy",
            }
        ),
        name="app-detail",
    ),
    path(
        "<uuid:uuid>/env-vars/", views.AppEnvVarAPIView.as_view(), name="app-env-vars"
    ),
    path(
        "<uuid:uuid>/build-vars/",
        views.AppBuildVarsAPIView.as_view(),
        name="app-build-vars",
    ),
    path("<uuid:uuid>/secrets/", views.AppSecretAPIView.as_view(), name="app-secrets"),
    path("<uuid:uuid>/volumes/", views.VolumesAPIView.as_view(), name="app-volumes"),
    path(
        "<uuid:app_uuid>/deployments/",
        DeploymentListCreateAPIView.as_view(),
        name="deployment-list-create",
    ),
    path(
        "<uuid:app_uuid>/custom-domains/",
        CustomDomainView.as_view(),
        name="custom-domain",
    ),
    path("<uuid:uuid>/init-process/", InitProcessView.as_view(), name="init-process"),
    path("<uuid:uuid>/worker/", WorkerProcessView.as_view(), name="worker"),
    path("<uuid:uuid>/autodeploy/", AutoDeployView.as_view(), name="autodeploy"),
    path(
        "<uuid:uuid>/liveness-probe/",
        LivenessProbeView.as_view(),
        name="liveness-probe",
    ),
    path("<uuid:uuid>/scale/", AppScaleView.as_view(), name="scale"),
]
