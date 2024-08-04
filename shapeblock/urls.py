from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.urls import path, include
from shapeblock.deployments.views import UpdateDeploymentView
from shapeblock.services.views import UpdateServiceDeploymentView
from rest_framework.authtoken import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(settings.ADMIN_URL, admin.site.urls),
    path('api/projects/', include('shapeblock.projects.urls')),
    path('api/apps/', include('shapeblock.apps.urls')),
    path('api/services/', include('shapeblock.services.urls')),
    path("service-deployments/", UpdateServiceDeploymentView.as_view(), name="service-deployments"),
    path("deployments/", UpdateDeploymentView.as_view(), name="deployments"),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/token/', views.obtain_auth_token),

]
