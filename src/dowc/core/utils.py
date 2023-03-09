import functools
import logging
from typing import Optional, Tuple, Union

import lxml.html
import requests
from requests.exceptions import HTTPError
from zds_client.client import ClientError
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.models import Service

from dowc.client import Client

logger = logging.getLogger(__name__)


def clean_token(token: str) -> str:
    for char in ["(", ")"]:
        token = token.replace(char, "")

    # Get token from <opaquetoken:<token>>
    token = lxml.html.fromstring(token).tag
    return token


def get_client(url: str) -> Client:
    """
    Gets drc client based on URL.
    """

    client = Service.get_client(url)
    if client is None:
        raise RuntimeError(f"Could not find a service for '{url}'")

    return client


def require_client(func):
    """
    Checks if decorated function has a client as a keyword argument,
    if it doesn't, it will add it to the keyword arguments.
    """

    @functools.wraps(func)
    def wrapped_func(*args, **kwargs):
        client = kwargs.get("client", None)
        if not client:
            url = args[0]
            kwargs["client"] = get_client(url)

        assert type(kwargs["client"]) == Client
        return func(*args, **kwargs)

    return wrapped_func


@require_client
def get_document(url: str, client: Optional[Client] = None) -> Document:
    """
    Gets a document by URL reference.
    """

    response = client.retrieve("enkelvoudiginformatieobject", url=url)
    # TODO CHECK RESPONSE IN CASE DOCUMENT DOESN'T EXIST
    return factory(Document, response)


@require_client
def lock_document(url: str, client: Optional[Client] = None) -> str:
    """
    Locks a document by URL reference.
    """

    lock_result = client.operation(
        "enkelvoudiginformatieobject_lock", data={}, url=f"{url}/lock"
    )
    lock = lock_result["lock"]
    return lock


@require_client
def unlock_document(
    url: str, lock: str, client: Optional[Client] = None
) -> Tuple[Union[str, Document], bool]:
    """
    Unlocks a document by URL reference.

    """
    try:
        client.request(
            f"{url}/unlock",
            "enkelvoudiginformatieobject_unlock",
            "POST",
            expected_status=204,
            json={"lock": lock},
        )
        doc_data = client.retrieve("enkelvoudiginformatieobject", url=url)
        return factory(Document, doc_data), True
    except (ClientError, HTTPError) as exc:
        logger.warning("Could not unlock {url}.".format(url=url), exc_info=True)
        return url, False


@require_client
def get_document_content(content_url: str, client: Optional[Client] = None) -> bytes:
    """
    Gets document content.
    """

    response = requests.get(content_url, headers=client.auth.credentials())
    response.raise_for_status()
    return response.content


@require_client
def update_document(
    url: str, data: dict, client: Optional[Client] = None
) -> Tuple[Union[str, Document], bool]:
    """
    Updates a document by URL reference.

    """
    try:
        response = client.partial_update(
            "enkelvoudiginformatieobject", data=data, url=url
        )
        return factory(Document, response), True
    except (ClientError, HTTPError) as exc:
        logger.warning("Could not update {url}.".format(url=url), exc_info=True)
        return url, False
