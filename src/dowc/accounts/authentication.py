import logging
from typing import Dict

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from requests.models import Request
from rest_framework import exceptions
from rest_framework.authentication import (
    TokenAuthentication as _TokenAuthentication,
    get_authorization_header,
)
from zgw_auth_backend.authentication import ZGWAuthentication as _ZGWAuthentication
from zgw_auth_backend.zgw import ZGWAuth

logger = logging.getLogger(__name__)


class ApplicationTokenAuthentication(_TokenAuthentication):
    keyword = "ApplicationToken"

    def authenticate_credentials(self, key):
        from .models import ApplicationToken

        try:
            token = ApplicationToken.objects.get(token=key)
        except ApplicationToken.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        return (None, token)


class ZGWAuthentication(_ZGWAuthentication):
    """
    Taken from zgw_auth_backend and adapted to further suit our needs.
    We want to include first and last names and check every authentication
    if an update is needed to reflect changes done to their first
    and last name.

    """

    def authenticate(self, request: Request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b"bearer":
            return None

        if len(auth) == 1:
            msg = _("Invalid bearer header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _(
                "Invalid bearer header. Credentials string should not contain spaces."
            )
            raise exceptions.AuthenticationFailed(msg)

        auth = ZGWAuth(auth[1].decode("utf-8"))

        user_id = auth.payload.get("user_id")
        if not user_id:
            msg = _("Invalid 'user_id' claim. The 'user_id' should not be empty.")
            raise exceptions.AuthenticationFailed(msg)

        email = auth.payload.get("email", "")
        return self.authenticate_user_id(user_id, email, auth.payload)

    def authenticate_user_id(self, username: str, email: str, payload: Dict):
        UserModel = get_user_model()
        fields = {UserModel.USERNAME_FIELD: username}
        user, created = UserModel._default_manager.get_or_create(**fields)
        if created:
            msg = "Created user object for username %s" % username
            logger.info(msg)

        if email:
            email_field = UserModel.get_email_field_name()
            email_value = getattr(user, email_field)
            if not email_value or email_value != email:
                setattr(user, email_field, email)
                user.save()
                msg = "Set email to %s of user with username %s" % (email, username)
                logger.info(msg)

        extra_user_info_fields = ["first_name", "last_name"]
        data = {
            field: value
            for field, value in payload.items()
            if field in extra_user_info_fields
        }
        for field, value in data.items():
            if not getattr(user, field) == value:
                setattr(user, field, value)
                try:
                    user.save(update_fields=[field])
                except ValueError:
                    logger.error(exc_info=True)
                    continue

        return (user, None)
