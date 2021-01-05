from django.urls import path

from .views import WebDavView

app_name = "core"

urlpatterns = [
    path(
        "<uuid:uuid>/<slug:token>/<path:path>",
        WebDavView.as_view(),
        name="webdav-document",
    ),
]
