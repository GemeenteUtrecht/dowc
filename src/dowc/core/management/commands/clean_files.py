from typing import List

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db.models import QuerySet

from zgw_consumers.concurrent import parallel

from dowc.core.constants import DocFileTypes
from dowc.core.data import EmailData
from dowc.core.managers import DowcQuerySet
from dowc.core.models import DocumentFile
from dowc.core.utils import unlock_document

class Command(BaseCommand):
    help = "Delete documentfile objects from the DoWC. Users that were in the middle of an editing process will be emailed."

    def handle(self, **options):
        self.bulk_delete_read_files()
        self.bulk_delete_write_files()

    def initialize_email_data(self):
        self.email_data: List[EmailData] = []

    def get_queryset(self, purpose: str) -> DowcQuerySet:
        return DocumentFile.objects.filter(purpose=purpose)

    def bulk_delete_read_files(self):
        read_docfiles = self.get_queryset(DocFileTypes.read)
        read_count = read_docfiles.count()
        read_docfiles.delete()
        failed = DocumentFile.objects.filter(
            purpose=DocFileTypes.read
        ).count()
        if failed > 0:
            raise CommandError("{read_count_failed} read documentfile objects failed to be deleted.")
        
        self.stdout.write(
            f"{read_docfiles.count()} 'read' documentfile objects were found and deleted."
        )

    def bulk_delete_write_files(self):
        write_docfiles = self.get_queryset(DocFileTypes.write)
        self.stdout.write(
            f"{len(write_docfiles)} 'write' documentfile objects are found."
        )

        # Initialize email_data
        self.initialize_email_data()

        # Unlock documents, mark them safe for deletion and extract email data
        self.unlock_documents_and_set_email_data(write_docfiles)

        # Delete the documentfile objects related to the unlocked documents
        self.delete_write_files()

        failed = self.get_queryset(DocFileTypes.write).count()
        if failed > 0:
             raise CommandError(f"{failed} 'write' documentfile objects failed to delete.")

    def unlock_documents_and_set_email_data(self, write_docfiles: DowcQuerySet):
        unlock_urls = []
        locks = []
        for docfile in write_docfiles:
            unlock_urls.append(docfile.drc_url)
            locks.append(docfile.lock)

        with parallel() as executor:
            results = executor.map(unlock_document, unlock_urls, locks)

        count = 0
        for document in results:
            for docfile in write_docfiles:
                if document.url in docfile.drc_url:
                    docfile.api_document = document
                    docfile.safe_for_deletion = True
                    self.email_data.append(
                        EmailData(
                            user=docfile.user,
                            filename=docfile.filename,
                            info_url=docfile.info_url,
                        )
                    )
                    count += 1
                    break

        DocumentFile.objects.bulk_update(
            write_docfiles, ["api_document", "safe_for_deletion"]
        )
        self.stdout.write(
            f"{count} 'write' documentfile objects are unlocked and marked for deletion."
        )

    def delete_write_files(self):
        write_docfiles = self.get_queryset(DocFileTypes.write).filter(
            safe_for_deletion=True
        )
        count = write_docfiles.count()
        write_docfiles.delete()
        self.stdout.write(f"{count} 'write' documentfile objects are deleted.")
