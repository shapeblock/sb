from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.ProjectViewSet, basename='project')

urlpatterns = [
    path('<uuid:uuid>/apps/', views.ProjectAppsView.as_view(), name='project-apps'),
    path('', include(router.urls)),
]

