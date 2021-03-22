from dataclasses import dataclass
from typing import Dict

from django.utils.translation import gettext_lazy as _

from dowc.accounts.models import User


@dataclass
class EmailData:
    filename: str
    info_url: str
    user: User

    @property
    def name(self) -> str:
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        if self.user.username:
            return self.user.username
        return _("user")

    def as_context(self) -> Dict[str, str]:
        return {"name": self.name, "filename": self.filename, "info_url": self.info_url}
