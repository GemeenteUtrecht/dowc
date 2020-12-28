from django.urls import path

from .views import GetDocumentView

app_name = "core"

urlpatterns = [
    path(
        "document/<str:uuid>/<str:token>/<str:filename>",
        GetDocumentView.as_view(),
        name="get-document",
    ),
]
