from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from dowc.accounts.models import User


@dataclass
class EmailData:
    user: User
    filename: str
    info_url: str

    @property
    def name(self, obj) -> str:
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        if user.username:
            return user.username
        return _("user")

    @property
    def email(self) -> str:
        return user.email
