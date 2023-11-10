from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class ResourceSubFolders(DjangoChoices):
    public = ChoiceItem("public", _("public"))
    protected = ChoiceItem("protected", _("Protected"))


class DocFileTypes(DjangoChoices):
    write = ChoiceItem("write", _("Write"))
    read = ChoiceItem("read", _("Read"))
    download = ChoiceItem("download", _("Download"))


EXTENSION_HANDLER = {
    ".doc": "ms-word",
    ".docm": "ms-word",
    ".docx": "ms-word",
    ".dot": "ms-word",
    ".dotm": "ms-word",
    ".dotx": "ms-word",
    ".htm": "ms-word",
    ".html": "ms-word",
    ".mht": "ms-word",
    ".mhtml": "ms-word",
    ".odt": "ms-word",
    ".rtf": "ms-word",
    ".txt": "ms-word",
    ".wps": "ms-word",
    ".xml": "ms-word",
    ".xps": "ms-word",
    ".csv": "ms-excel",
    ".dbf": "ms-excel",
    ".dif": "ms-excel",
    ".ods": "ms-excel",
    ".prn": "ms-excel",
    ".slk": "ms-excel",
    ".xla": "ms-excel",
    ".xlam": "ms-excel",
    ".xls": "ms-excel",
    ".xlsb": "ms-excel",
    ".xlsm": "ms-excel",
    ".xlsx": "ms-excel",
    ".xlt": "ms-excel",
    ".xltm": "ms-excel",
    ".xltx": "ms-excel",
    ".xlw": "ms-excel",
    ".emf": "ms-powerpoint",
    ".odp": "ms-powerpoint",
    ".pot": "ms-powerpoint",
    ".potm": "ms-powerpoint",
    ".potx": "ms-powerpoint",
    ".ppa": "ms-powerpoint",
    ".ppam": "ms-powerpoint",
    ".pps": "ms-powerpoint",
    ".ppsm": "ms-powerpoint",
    ".ppsx": "ms-powerpoint",
    ".ppt": "ms-powerpoint",
    ".pptm": "ms-powerpoint",
    ".pptx": "ms-powerpoint",
    ".thmx": "ms-powerpoint",
}


DOCUMENT_COULD_NOT_BE_UNLOCKED = "Document could not be unlocked on DRC."
DOCUMENT_COULD_NOT_BE_UPDATED = "Document could not be updated on DRC."
