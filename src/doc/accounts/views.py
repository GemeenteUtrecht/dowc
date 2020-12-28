from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import SuccessURLAllowedHostsMixin
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.http import is_safe_url
from django.views.generic import RedirectView

from django_auth_adfs_db.models import ADFSConfig


class RedirectToLoginView(SuccessURLAllowedHostsMixin, RedirectView):
    """
    Redirect the user to the correct auth handler.

    If ADFS is enabled, the user will be sent to django_auth_adfs' login views.
    Otherwise, the user is redirected to the admin login page.
    """

    redirect_field_name = REDIRECT_FIELD_NAME

    def get_redirect_url(self, *args, **kwargs):
        # redirect to ADFS if ADFS is enabled
        adfs_config = ADFSConfig.get_solo()
        if adfs_config.enabled:
            redirect_path = reverse("django_auth_adfs:login")
        # fall back to admin login
        else:
            redirect_path = reverse("admin:login")

        return redirect_path
