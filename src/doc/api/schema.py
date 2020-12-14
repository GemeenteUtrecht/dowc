import logging

from rest_framework import viewsets
from rest_framework.schemas.openapi import (
    AutoSchema as _AutoSchema,
    SchemaGenerator as _SchemaGenerator,
)
from rest_framework.schemas.utils import is_list_view

logger = logging.getLogger(__name__)


class SchemaGenerator(_SchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request=request, public=public)
        if request is not None:
            _root = request.META["SCRIPT_NAME"] or "/"
            root = request.build_absolute_uri(_root)
            schema["servers"] = [{"url": root.rstrip("/")}]
        return schema


class AutoSchema(_AutoSchema):
    method_mapping = {
        "get": "retrieve",
        "post": "create",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }

    def _get_operation_id(self, path, method) -> str:
        """
        Compute the model name as lowercase string, postfixed with the operation name.
        """
        method_name = getattr(self.view, "action", method.lower())
        if is_list_view(path, method, self.view):
            action = "list"
        elif method_name not in self.method_mapping:
            action = method_name
        else:
            action = self.method_mapping[method.lower()]

        # Try to deduce the ID from the view's model
        if isinstance(self.view, viewsets.GenericViewSet):
            model = getattr(getattr(self.view, "queryset", None), "model", None)
            if not model:
                logger.warning(
                    "Could not determine operation ID for path '%s' and method '%s'. Falling back to default.",
                    path,
                    method,
                )
                return super()._get_operation_id(path, method)

            name = model._meta.model_name
            return f"{name}_{action}"
        else:
            if hasattr(self.view, "get_serializer_class"):
                name = self.view.get_serializer_class().__name__
                if name.endswith("Serializer"):
                    name = name[:-10]
            else:
                logger.warning(
                    "Could not determine operation ID for path '%s' and method '%s'. Falling back to default.",
                    path,
                    method,
                )
                return super()._get_operation_id(path, method)

            name = name.lower()
            return f"{name}_{action}"
