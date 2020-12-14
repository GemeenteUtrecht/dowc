import base64
from typing import NoReturn, Optional

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.client import ZGWClient
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.service import get_paginated_results


def get_client(url: str) -> ZGWClient:
    """
    Gets drc client based on URL.
    """
    client = Service.get_client(url)
    if client is None:
        raise RuntimeError(f"Could not find a service for '{url}'")

    return client


def check_client(func):
    """
    Checks if decorated function has a client as a keyword argument,
    if it doesn't, it will add it to the keyword arguments.
    """

    def wrapped_func(*args, **kwargs):
        client = kwargs.get("client", None)
        if not client:
            url = args[0]
            kwargs["client"] = get_client(url)
        return func(*args, **kwargs)

    return wrapped_func


@check_client
def get_document(url: str, client: Optional[ZGWClient] = None) -> Document:
    """
    Gets a document by URL reference.
    """

    response = client.retrieve("enkelvoudiginformatieobject", url=url)
    return factory(Document, response)


@check_client
def lock_document(url: str, client: Optional[ZGWClient] = None) -> str:
    """
    Locks a document by URL reference.
    """

    lock_result = client.operation(
        "enkelvoudiginformatieobject_lock", data={}, url=f"{url}/lock"
    )
    lock = lock_result["lock"]
    return lock


@check_client
def unlock_document(
    url: str, lock: str, client: Optional[ZGWClient] = None
) -> NoReturn:
    """
    Unlocks a document by URL reference.
    """

    client.request(
        f"{url}/unlock",
        "enkelvoudiginformatieobject_unlock",
        "POST",
        expected_status=204,
        json={"lock": lock},
    )


def update_document(url: str, file: UploadedFile, data: dict) -> Document:
    """
    Updates a document by URL reference.
    """
    client = get_client(url)
    content = base64.b64encode(file.read()).decode("utf-8")
    data["inhoud"] = content
    response = client.partial_update("enkelvoudiginformatieobject", data=data, url=url)
    document = factory(Document, response)
    return factory(Document, _doc)
