from django.conf import settings

from djangodav.base.resources import MetaEtagMixIn
from djangodav.fs.resources import DummyFSDAVResource


class WebDavResource(MetaEtagMixIn, DummyFSDAVResource):
    root = settings.PRIVATE_MEDIA_ROOT
