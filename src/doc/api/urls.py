from django.urls import include, path
from django.utils.translation import gettext as _

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)
from rest_framework import permissions, routers

from .views import remote_schema_view
from .viewsets import DocumentFileViewset

router = routers.SimpleRouter(trailing_slash=False)
router.register("documenten", DocumentFileViewset)

urlpatterns = [
    # API schema documentation
    path("v1", SpectacularJSONAPIView.as_view(schema=None), name="api-schema-json"),
    path("v1/_get-remote-schema/", remote_schema_view, name="get-remote-schema"),
    path("v1/schema", SpectacularAPIView.as_view(schema=None), name="api-schema"),
    path(
        "v1/docs/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-docs"
    ),
    path("", include(router.urls)),
]
