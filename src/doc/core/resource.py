import shutil

from django.conf import settings

from djangodav.base.resources import MetaEtagMixIn
from djangodav.fs.resources import BaseFSDavResource


class WebDavResource(MetaEtagMixIn, BaseFSDavResource):
    root = settings.PRIVATE_MEDIA_ROOT

    def read(self):
        with open(self.get_abs_path(), "rb") as f:
            return f.read()

    def write(self, request):
        with open(self.get_abs_path(), "wb") as dst:
            shutil.copyfileobj(request, dst)
