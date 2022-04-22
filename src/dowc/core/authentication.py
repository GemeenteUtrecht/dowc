from django.contrib.auth import authenticate

from django_auth_adfs.config import provider_config
from django_auth_adfs_db.models import ADFSConfig
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header


def get_www_authenticate_header():
    provider_config.load_config()
    authorization_uri = provider_config.authorization_endpoint
    trusted_issuer = provider_config.issuer

    config = ADFSConfig.get_solo()
    client_id = config.client_id
    return f"Bearer authorization_uri={authorization_uri}"


class AdfsAccessTokenAuthentication(BaseAuthentication):
    """
    ADFS access Token authentication
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
        return get_www_authenticate_header()
