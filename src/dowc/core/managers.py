from typing import List, Tuple

from django.db import models
from django.db.models.deletion import Collector

from zgw_consumers.api_models.documenten import Document
from zgw_consumers.concurrent import parallel

from dowc.core.utils import unlock_document, update_document

from .constants import (
    DOCUMENT_COULD_NOT_BE_UNLOCKED,
    DOCUMENT_COULD_NOT_BE_UPDATED,
    DocFileTypes,
)


class DowcQuerySet(models.QuerySet):
    """
    This QuerySet is adapted to deal with the complexities
    of deleting objects that have potentially locked objects
    on the DRC API.

    Force delete will attempt to unlock the document in the
    DRC API and then continue to delete.
    """

    def delete(self) -> Tuple[int, dict]:
        qs = self._chain()
        deletion_query = qs.filter(
            purpose__in=[DocFileTypes.read, DocFileTypes.download]
        ) | qs.filter(safe_for_deletion=True) & qs.filter(error=False)
        collector = Collector(using=deletion_query.db)
        collector.collect(deletion_query)
        deleted, _rows_count = collector.delete()
        return deleted, _rows_count

    def _bulk_update_on_drc(
        self, documents: models.QuerySet
    ) -> List[Tuple[Document, bool]]:
        documents_to_be_updated = []
        urls = []
        for document in documents:
            changed_doc = document.update_drc_document()
            if changed_doc:
                documents_to_be_updated.append(changed_doc)
                urls.append(document.unversioned_url)

        with parallel() as executor:
            results = list(executor.map(update_document, urls, documents_to_be_updated))
        return results

    def handle_errors(self, errored_docs: List[str], error_msg: str = ""):
        qs = self._chain()
        qs = qs.filter(unversioned_url__in=errored_docs, purpose=DocFileTypes.write)
        for doc in qs:
            doc.error = True
            doc.error_msg = error_msg
        self.bulk_update(qs, ["error", "error_msg"])

    def force_delete(self) -> int:
        qs = self._chain()

        # Get all documentfile objects with the purpose 'write' and which have not yet been marked as safe for deletion
        unsafe_for_deletion = qs.filter(
            purpose=DocFileTypes.write, safe_for_deletion=False, error=False
        ).all()

        # Update documents on DRC
        results = self._bulk_update_on_drc(unsafe_for_deletion)

        # Handle any errors and filter documents that didn't error out:
        self.handle_errors(
            [doc for doc, success in results if not success],
            error_msg=DOCUMENT_COULD_NOT_BE_UPDATED,
        )
        unsafe_for_deletion = unsafe_for_deletion.all()

        # Initialize empty lists for the drc urls and the related locks
        unlock_urls = []
        locks = []
        # Get urls and locks
        for docfile in unsafe_for_deletion:
            unlock_urls.append(docfile.unversioned_url)
            locks.append(docfile.lock)

        # Send unlock requests to drc in parallel
        with parallel() as executor:
            results = list(executor.map(unlock_document, unlock_urls, locks))

        # Handle any errors and filter documents that didn't error out:
        self.handle_errors(
            [doc for doc, success in results if not success],
            error_msg=DOCUMENT_COULD_NOT_BE_UNLOCKED,
        )
        unsafe_for_deletion = unsafe_for_deletion.all()

        # Mark safe for deletion
        for docfile in unsafe_for_deletion:
            docfile.safe_for_deletion = True
            docfile.force_deleted = True

        # Bulk update the safe_for_deletion field
        self.bulk_update(unsafe_for_deletion, ["safe_for_deletion", "force_deleted"])

        # Call 'normal' delete method on object to send email
        deleted = 0
        for docfile in unsafe_for_deletion:
            docfile.delete()
            deleted += 1

        read_deleted, _ = self.delete()
        return deleted + read_deleted
