import logging
from typing import List

from django.core.management import BaseCommand, CommandError

from dowc.core.constants import DocFileTypes
from dowc.core.managers import DowcQuerySet
from dowc.core.models import DocumentFile, DocumentLock
from dowc.emails.data import EmailData

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete documentfile objects and related objects from the DoWC. Users that were in the middle of an editing process will be emailed."

    def handle(self, **options):
        self.bulk_delete_read_files()
        self.bulk_delete_write_files()
        self.bulk_delete_locks()

    def bulk_delete_read_files(self):
        read_qs = DocumentFile.objects.filter(purpose=DocFileTypes.read)
        count = read_qs.count()
        self.stdout.write(f"Found {count} 'read' documentfile object(s).")
        if count > 0:
            deleted, rest = read_qs.delete()
            self.stdout.write(f"Deleted {deleted} 'read' documentfile object(s).")

            # Make sure no read documentfile objects remain
            if count - deleted > 0:
                logger.error(
                    f"{count - deleted} 'read' documentfile object(s) failed to be deleted."
                )

    def bulk_delete_write_files(self):
        write_qs = DocumentFile.objects.select_related("user").filter(
            purpose=DocFileTypes.write
        )
        count = write_qs.count()
        self.stdout.write(f"Found {count} 'write' documentfile object(s).")
        if count > 0:
            # Delete the documentfile objects related to the unlocked documents
            deleted = DocumentFile.objects.force_delete()
            self.stdout.write(f"Unlocked {deleted} document(s).")
            self.stdout.write(f"Deleted {deleted} 'write' documentfile object(s).")

            # Make sure no write documentfile objects remain
            if not count - deleted == 0:
                logger.warning(
                    f"{count - deleted} 'write' documentfile objects failed to be deleted."
                )

    def bulk_delete_locks(self):
        DocumentLock.objects.all().delete()
