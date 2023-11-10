from django.urls import include, path
from django.utils.translation import gettext as _

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)
from rest_framework import routers

from .views import SupportedFileExtensionsView
from .viewsets import DocumentFileViewset

router = routers.SimpleRouter(trailing_slash=False)
router.register("documenten", DocumentFileViewset)

urlpatterns = [
    # API schema documentation
    path("v1", SpectacularJSONAPIView.as_view(schema=None), name="api-schema-json"),
    path(
        "v1/",
        include(
            [
                path(
                    "schema/",
                    SpectacularAPIView.as_view(schema=None),
                    name="api-schema",
                ),
                path(
                    "docs/",
                    SpectacularRedocView.as_view(url_name="api-schema"),
                    name="api-docs",
                ),
                path("", include(router.urls)),
            ],
        ),
    ),
    path(
        "file-extensions", SupportedFileExtensionsView.as_view(), name="file-extensions"
    ),
]
