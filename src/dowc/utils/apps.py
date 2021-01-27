from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "dowc.utils"

    def ready(self):
        from . import checks  # noqa
