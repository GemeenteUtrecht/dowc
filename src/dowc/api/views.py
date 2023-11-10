from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from dowc.accounts.authentication import ApplicationTokenAuthentication
from dowc.accounts.permissions import HasTokenAuth
from dowc.core.constants import EXTENSION_HANDLER

from .serializers import SupportedFileExtensionsSerializer


class SupportedFileExtensionsView(APIView):
    authentication_classes = [
        ApplicationTokenAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = (HasTokenAuth | IsAuthenticated,)

    @extend_schema(
        summary=_("Retrieve supported file extensions documents."),
        request=None,
        responses={200: SupportedFileExtensionsSerializer},
    )
    def get(self, request):
        extensions = sorted(list(EXTENSION_HANDLER.keys()))
        serializer = SupportedFileExtensionsSerializer({"extensions": extensions})
        return Response(serializer.data)
