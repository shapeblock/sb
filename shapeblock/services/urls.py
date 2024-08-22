from django.urls import path
from . import views

urlpatterns = [
    path(
        "",
        views.ServiceViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="cluster",
    ),
    path(
        "<uuid:uuid>/",
        views.ServiceViewSet.as_view(
            {
                "get": "retrieve",
                "delete": "destroy",
            }
        ),
        name="cluster-detail",
    ),
    path("<uuid:uuid>/attach/", views.AttachAppView.as_view(), name="attach-app"),
    path("<uuid:uuid>/detach/", views.DetachAppView.as_view(), name="detach-app"),
]
