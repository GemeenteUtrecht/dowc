from django.urls import path

from .views import get_document

app_name = "core"

urlpatterns = [
    path("document/open", get_document, name="get-document"),
]
