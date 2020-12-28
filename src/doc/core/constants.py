from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class DocFileTypes(DjangoChoices):
    edit = ChoiceItem("edit", _("Edit"))
    read = ChoiceItem("read", _("Read"))
