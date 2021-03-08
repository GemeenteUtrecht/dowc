from typing import List

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _

from zgw_consumers.concurrent import parallel

from .data import EmailData
from .serializers import EmailSerializer

TEMPLATE_PATH = "emails/base.txt"


def send_bulk_emails(email_data: List[EmailData]) -> int:
    with parallel() as executor:
        results = executor.map(send_email, email_data)

    return len(list(results))


def send_email(email_data: EmailData):
    email_template = get_template(TEMPLATE_PATH)
    context = EmailSerializer(instance=email_data).data
    email_message = email_template.render(context)
    email = EmailMessage(
        subject=_("We saved your unfinished document: {filename}").format(
            filename=context["filename"]
        ),
        body=email_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        reply_to=[settings.DEFAULT_FROM_EMAIL],
        to=[context["email"]],
    )
    email.send(fail_silently=False)
