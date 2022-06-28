from typing import Dict

from django.conf import settings
from django.urls import reverse

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication


def get_authenticate_headers(request) -> Dict[str, str]:
    return {
        "X-FORMS_BASED_AUTH_REQUIRED": request.build_absolute_uri(
            reverse("rest_framework:login")
        ),
        "X-FORMS_BASED_AUTH_RETURN_URL": request.build_absolute_uri(
            settings.LOGIN_REDIRECT_URL
        ),
        "X-FORMS_BASED_AUTH_DIALOG_SIZE": "800x600",
    }


class WebDavADFSAuthentication(BaseAuthentication):
    """
    ADFS access Token authentication

    The WebDAV client requires specific headers to be returned
    in case the user is not authenticated and is to be authenticated
    through MS-OFBA.

    In our case we want to enable OIDC/ADFS login.

    First a response to a non authenticated user needs to return
    the 403 status code.

    Then the client requires the header:
        X-FORMS_BASED_AUTH_REQUIRED: <ADFS login url>

    The following headers are optional:
        X-FORMS_BASED_AUTH_RETURN_URL: <on success url> (if not submitted, is assumed to be the same as X-FORMS_BASED_AUTH_REQUIRED)
        X-FORMS_BASED_AUTH_DIALOG_SIZE: <pixels_x: int>x<pixels_y:int>

    as well as a 403 status code to be returned.
    """

    def authenticate(self, request):
        """
        Returns a `User` if a correct access token has been supplied
        in the Authorization header.  Otherwise returns `None`.
        """

        user = getattr(request._request, "user", None)
        if not user or not user.is_authenticated:
            raise exceptions.AuthenticationFailed(
                "Did not find user. Please login through OIDC."
            )
        # Authenticate the user
        # The AdfsAuthCodeBackend authentication backend will notice the "access_token" parameter
        # and skip the request for an access token using the authorization code
        return user, None

    def authenticate_header(self, request):
        return get_authenticate_headers(request)
