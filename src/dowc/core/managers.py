from typing import Tuple

from django.db import models
from django.db.models.deletion import Collector

from zgw_consumers.concurrent import parallel

from dowc.core.utils import unlock_document, update_document

from .constants import DocFileTypes


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
        deletion_query = qs.filter(purpose=DocFileTypes.read) | qs.filter(
            safe_for_deletion=True
        )
        collector = Collector(using=deletion_query.db)
        collector.collect(deletion_query)
        deleted, _rows_count = collector.delete()
        return deleted, _rows_count

    def _bulk_update_on_drc(self, documents: models.QuerySet):
        documents_to_be_updated = []
        urls = []
        for document in documents:
            changed_doc = document.update_drc_document()
            if changed_doc:
                documents_to_be_updated.append(changed_doc)
                urls.append(document.unversioned_url)

        with parallel() as executor:
            executor.map(update_document, urls, documents_to_be_updated)

    def force_delete(self) -> Tuple[int, dict]:
        qs = self._chain()

        # Get all documentfile objects with the purpose 'write' and which have not yet been marked as safe for deletion
        unsafe_for_deletion = qs.filter(
            purpose=DocFileTypes.write, safe_for_deletion=False
        )

        # Update documents on DRC
        self._bulk_update_on_drc(unsafe_for_deletion)

        # Initialize empty lists for the drc urls and the related locks
        unlock_urls = []
        locks = []
        # Get urls and locks
        for docfile in unsafe_for_deletion:
            unlock_urls.append(docfile.unversioned_url)
            locks.append(docfile.lock)

        # Send unlock requests to drc in parallel
        with parallel() as executor:
            results = executor.map(unlock_document, unlock_urls, locks)

        # Match results with query to double check and mark safe for deletion
        for document in results:
            for docfile in unsafe_for_deletion:
                if document.url == docfile.unversioned_url:
                    docfile.safe_for_deletion = True

        # Bulk update the safe_for_deletion field
        self.bulk_update(unsafe_for_deletion, ["safe_for_deletion"])

        # Call 'normal' delete method
        deleted, _rows_count = self.delete()
        return deleted, _rows_count
