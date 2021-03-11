from typing import List

from django.conf import settings
from django.core.mail import send_mass_mail
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _

from .data import EmailData
from .serializers import EmailSerializer

TEMPLATE_PATH = "emails/base.txt"
SUBJECT = _("We saved your unfinished document: {filename}")


def send_emails(email_data: List[EmailData]) -> int:
    email_template = get_template(TEMPLATE_PATH)
    data = EmailSerializer(instance=email_data, many=True).data
    emails = []
    for email in data:
        email_message = email_template.render(email)
        emails.append(
            (
                SUBJECT.format(filename=email["filename"]),
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                [email["email"]],
            )
        )

    results = send_mass_mail(emails, fail_silently=False)
    return results
