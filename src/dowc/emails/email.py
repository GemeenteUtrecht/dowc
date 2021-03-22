import logging
from typing import List

from django.conf import settings
from django.core.mail import send_mass_mail
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _

from .data import EmailData

logger = logging.getLogger(__name__)

TEMPLATE_PATH = "emails/base.txt"
SUBJECT = _("We saved your unfinished document: {filename}")


def send_emails(email_data: List[EmailData]) -> int:
    email_template = get_template(TEMPLATE_PATH)
    emails = []
    for email in email_data:
        if email.user.email:
            email_message = email_template.render(email.as_context())
            emails.append(
                (
                    SUBJECT.format(filename=email.filename),
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email.user.email],
                )
            )
        else:
            logger.warning(
                f"User with username {email.user.username} has no known email address."
            )

    results = send_mass_mail(emails, fail_silently=False)
    return results
