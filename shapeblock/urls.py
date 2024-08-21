from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.urls import path, include
from shapeblock.deployments.views import UpdateDeploymentView, PodInfoView
from shapeblock.services.views import UpdateServiceDeploymentView
from shapeblock.apps.views import ShellInfoView
from rest_framework.authtoken import views
from shapeblock.authentication.views import AddUserGithubTokenAPIView, GithubClientInfoAPIView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(settings.ADMIN_URL, admin.site.urls),
    path('api/projects/', include('shapeblock.projects.urls')),
    path('api/apps/', include('shapeblock.apps.urls')),
    path('api/services/', include('shapeblock.services.urls')),
    path("service-deployments/", UpdateServiceDeploymentView.as_view(), name="service-deployments"),
    path("deployments/", UpdateDeploymentView.as_view(), name="deployments"),
    path("deployments/<uuid:deployment_uuid>/pod-info/", PodInfoView.as_view(), name="pod-info"),
    path("apps/<uuid:app_uuid>/shell-info/", ShellInfoView.as_view(), name="shell-info"),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/github-token/', AddUserGithubTokenAPIView.as_view(), name='github-token'),
    path('api/github-client/', GithubClientInfoAPIView.as_view(), name='github-client-info'),
]
