from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from dowc.accounts.models import User


@dataclass
class EmailData:
    filename: str
    info_url: str
    user: User
