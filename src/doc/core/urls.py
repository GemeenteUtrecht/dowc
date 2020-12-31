from django.urls import path

from .views import WebDavView

app_name = "core"

urlpatterns = [
    path(
        "document/<str:uuid>/<str:token>/<str:filename>",
        WebDavView.as_view(),
        name="webdav-document",
    ),
]
