import tempfile
from urllib.parse import urlsplit

from django.urls.resolvers import URLResolver

from dowc.urls import urlpatterns

tmpdir = tempfile.mkdtemp()


def get_url_kwargs(magic_url) -> dict:
    # Get keyword arguments from pattern in urlpatterns from url
    rel_url = urlsplit(magic_url.split("|u|")[-1]).path
    if rel_url.startswith("/"):
        rel_url = rel_url[1:]

    # Check urlpatterns for match - hard fail if it can't find a match.
    for urlpattern in urlpatterns:
        if isinstance(urlpattern, URLResolver):
            if urlpattern.app_name == "core":
                match = urlpattern.resolve(rel_url)
                if match:
                    return match.kwargs

    raise RuntimeError("Something is wrong with the URL.")
