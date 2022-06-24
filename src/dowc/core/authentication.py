from typing import Dict

from django.contrib.auth import authenticate

from django_auth_adfs.config import provider_config
from django_auth_adfs_db.models import ADFSConfig
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header


def get_authenticate_headers() -> Dict[str, str]:
    provider_config.load_config()
    authorization_uri = provider_config.authorization_endpoint
    return {
        "X-FORMS_BASED_AUTH_REQUIRED": authorization_uri,
        "X-FORMS_BASED_AUTH_RETURN_URL": authorization_uri,
    }


class AdfsAccessTokenAuthentication(BaseAuthentication):
    """
    ADFS access Token authentication

    The WebDAV client requires a special protocol to be able
    to use MS OFBA.
    If not authenticated, it requires the headers:
        X-FORMS_BASED_AUTH_REQUIRED
        X-FORMS_BASED_AUTH_RETURN_URL (if not submitted, is assumed to be the same as X-FORMS_BASED_AUTH_REQUIRED)
    as well as a 403 status code to be returned.
    """

    def authenticate(self, request):
        """
        Returns a `User` if a correct access token has been supplied
        in the Authorization header.  Otherwise returns `None`.
        """
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b"bearer":
            return None

        if len(auth) == 1:
            msg = "Invalid authorization header. No credentials provided."
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = (
                "Invalid authorization header. Access token should not contain spaces."
            )
            raise exceptions.AuthenticationFailed(msg)

        # Authenticate the user
        # The AdfsAuthCodeBackend authentication backend will notice the "access_token" parameter
        # and skip the request for an access token using the authorization code
        user = authenticate(access_token=auth[1])

        if user is None:
            raise exceptions.AuthenticationFailed("Invalid access token.")

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        return user, auth[1]

    def authenticate_header(self, request):
        return get_authenticate_headers()
