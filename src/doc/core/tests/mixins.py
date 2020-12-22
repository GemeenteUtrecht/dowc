import uuid

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from doc.core.tests.utils import generate_oas_component, mock_service_oas_get


class SetUpMockMixin:
    DRC_URL = "https://some.drc.nl/api/v1/"

    @classmethod
    def setUpTestData(self):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.drc, api_root=self.DRC_URL)

    def setUpMock(self, m):
        # Mock drc_client service
        mock_service_oas_get(m, self.DRC_URL, "drc")

        # Create mock url for drc object
        _uuid = str(uuid.uuid4())
        self.test_doc_url = f"{self.DRC_URL}enkelvoudiginformatieobjecten/{_uuid}"

        # Create mock url for drc document content download
        self.test_doc_download_url = f"{self.test_doc_url}/download"

        # Create mock document data from drc
        self.doc_data = generate_oas_component(
            "drc", "schemas/EnkelvoudigInformatieObject",
        )
        self.bestandsnaam = "bestandsnaam.docx"
        self.doc_data.update(
            {
                "bestandsnaam": self.bestandsnaam,
                "inhoud": self.test_doc_download_url,
                "url": self.test_doc_url,
            }
        )

        # Create mock call for eio from DRC
        m.get(self.test_doc_url, json=self.doc_data)

        # Create fake content
        self.content = b"Beetje aan het testen.".decode("utf-8")

        # Create mock call for content of eio
        m.get(self.test_doc_download_url, json=self.content)

        # Create mock url for locking of drc object
        self.test_doc_lock_url = f"{self.test_doc_url}/lock"

        # Create random lock data
        self.lock = uuid.uuid4().hex

        # Create mock call for locking of a document
        m.post(self.test_doc_lock_url, json={"lock": self.lock})
