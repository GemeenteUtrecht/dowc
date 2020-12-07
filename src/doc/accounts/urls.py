from django.urls import path

from .views import RedirectToLoginView

app_name = "accounts"

urlpatterns = [
    path("login", RedirectToLoginView.as_view(), name="login"),
]
