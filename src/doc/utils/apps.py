from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "doc.utils"

    def ready(self):
        from . import checks  # noqa
