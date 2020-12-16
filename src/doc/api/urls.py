from django.urls import include, path
from django.utils.translation import gettext as _

from rest_framework import permissions, routers
from rest_framework.schemas import get_schema_view

from .schema import SchemaGenerator
from .viewsets import DocumentFileViewset

description = """
D.O.C. facilitates reading and editing centrally located documents on local clients.
This API provides an interface to request the URL required to read/edit a document and 
requires authentication using a token obtained from an administrator.

Use the token in the `Authorization` header:

    Authorization: Token <token value>
"""

schema_view = get_schema_view(
    title=_("D.O.C. - read and edit documents"),
    description=description,
    version="1.0.0",
    generator_class=SchemaGenerator,
    permission_classes=(permissions.AllowAny,),
    public=True,
)

router = routers.SimpleRouter(trailing_slash=False)
router.register("documenten", DocumentFileViewset)

urlpatterns = [
    path("v1", schema_view, name="openapi-schema"),
    path("v1/", include(router.urls)),
]
