from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views.generic.base import TemplateView

handler500 = "dowc.utils.views.server_error"
admin.site.site_header = "dowc admin"
admin.site.site_title = "dowc admin"
admin.site.index_title = "Welcome to the dowc admin"

urlpatterns = [
    path(
        "admin/password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path(
        "admin/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path("admin/hijack/", include("hijack.urls")),
    path("admin/", admin.site.urls),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    # auth backends
    path("adfs/", include("django_auth_adfs.urls")),
    path("api/", include("dowc.api.urls")),
    # User facing pages
    path("", TemplateView.as_view(template_name="index.html"), name="index"),
    path("accounts/", include("dowc.accounts.urls")),
    path("core/", include("dowc.core.urls")),
]

# NOTE: The staticfiles_urlpatterns also discovers static files (ie. no need to run collectstatic). Both the static
# folder and the media folder are only served via Django if DEBUG = True.
urlpatterns += staticfiles_urlpatterns() + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)

if settings.DEBUG and apps.is_installed("debug_toolbar"):
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
