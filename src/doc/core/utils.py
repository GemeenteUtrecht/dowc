import glob
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

    if not response:
        raise InvalidURLException(f"A document couldn't be found with url: {url}")

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


def find_document(path):
    """
    The base assumption is that it's possible to change the filename 
    of a document.

    This implies the DocumentFile.document.path will not be accurate anymore.
    This will try and locate the last modified document in the folder.

    It is NOT permitted to change file extension.
    """
    # In case filename has changed
    dir_path = os.path.dirname(path)

    # Get files
    _fpath, file_extension = os.path.splitext(path)
    files_path = os.path.join(dir_path, f"*{file_extension}")
    filenames = glob.glob(files_path)

    # Get last modified file
    lmt_old = 0
    if filenames:
        for fn in filenames:
            lmt_new = os.path.getmtime(fn)
            if lmt_new > lmt_old:
                last_modified_file = fn

        return last_modified_file

    raise FilesNotFoundInFolder(f"No files were found in {dir_path}")
