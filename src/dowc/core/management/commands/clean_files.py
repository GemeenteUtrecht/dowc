import logging
from typing import List

from django.core.management import BaseCommand, CommandError

from dowc.core.constants import DocFileTypes
from dowc.core.managers import DowcQuerySet
from dowc.core.models import DocumentFile, DocumentLock
from dowc.emails.data import EmailData
from dowc.emails.email import send_emails

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
            # Extract email data
            email_data = self.get_email_data(write_qs)

            # Not sure yet what to assert with results
            results = send_emails(email_data)

            # Delete the documentfile objects related to the unlocked documents
            deleted, rest = DocumentFile.objects.force_delete()
            self.stdout.write(f"Unlocked {deleted} document(s).")
            self.stdout.write(f"Deleted {deleted} 'write' documentfile object(s).")

            # Make sure no write documentfile objects remain
            if not count - deleted == 0:
                logger.error(
                    f"{count - deleted} 'write' documentfile objects failed to be deleted."
                )

    def get_email_data(self, write_docfiles: DowcQuerySet) -> List[EmailData]:
        email_data = []
        for docfile in write_docfiles:
            if not docfile.safe_for_deletion:
                email_data.append(
                    EmailData(
                        user=docfile.user,
                        filename=docfile.filename,
                        info_url=docfile.info_url,
                    )
                )
        return email_data

    def bulk_delete_locks(self):
        DocumentLock.objects.all().delete()
