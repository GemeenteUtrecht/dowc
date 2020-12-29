import functools
import os
from typing import NoReturn, Optional

import requests
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.client import ZGWClient
from zgw_consumers.models import Service

from .exceptions import FilesNotFoundInFolder, InvalidURLException


def get_client(url: str) -> ZGWClient:
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
        return func(*args, **kwargs)

    return wrapped_func


@require_client
def get_document(url: str, client: Optional[ZGWClient] = None) -> Document:
    """
    Gets a document by URL reference.
    """

    response = client.retrieve("enkelvoudiginformatieobject", url=url)
    # TODO CHECK RESPONSE IN CASE DOCUMENT DOESNT EXIST
    return factory(Document, response)


@require_client
def lock_document(url: str, client: Optional[ZGWClient] = None) -> str:
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


@require_client
def get_document_content(content_url: str, client: Optional[ZGWClient] = None) -> str:
    """
    Gets document content.
    """

    response = requests.get(content_url, headers=client.auth.credentials())
    response.raise_for_status()
    return response.content


@require_client
def update_document(
    url: str, data: dict, client: Optional[ZGWClient] = None
) -> Document:
    """
    Updates a document by URL reference.
    """

    client = get_client(url)
    response = client.partial_update("enkelvoudiginformatieobject", data=data, url=url)
    return factory(Document, response)


def delete_files(instance):
    """
    Deletes files from a DocumentFile instance
    """

    storage = instance.document.storage
    name = instance.document.name

    if name:
        if storage.exists(name):
            storage.delete(name)

    original_storage = instance.original_document.storage
    original_name = instance.original_document.name

    if original_name:
        if original_storage.exists(original_name):
            original_storage.delete(original_name)


def rollback_file_creation(logger):
    """
    On failed saves we don't want to deal with garbage data hanging around.
    This ensures we delete those files in case .
    """

    def rollback_file_creation_inner(save):
        @functools.wraps(save)
        def wrapper(instance, **kwargs):
            try:
                return save(instance, **kwargs)

            except:
                logger.error(
                    "Something went wrong with saving the documentfile object.",
                    exc_info=True,
                )
                delete_files(instance)

        return wrapper

    return rollback_file_creation_inner
