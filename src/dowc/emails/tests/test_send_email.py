from django.core import mail
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from ..email import send_emails
from .factories import EmailDataFactory


class SendEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.email_data = EmailDataFactory.create()

    def test_send_email_success(self):
        result = send_emails([self.email_data])

        self.assertEqual(result, 1)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.body,
            "Beste {name},\n\n".format(name=self.email_data.user.username)
            + "Uw openstaande document {filename} is gesloten en de wijzigingen zijn doorgevoerd.\n".format(
                filename=self.email_data.filename
            )
            + "U kunt uw document vinden als u de volgende link volgt: {info_url}\n\n".format(
                info_url=self.email_data.info_url
            )
            + "Met vriendelijke groeten,\n\nFunctioneel Beheer Gemeente Utrecht",
        )
        self.assertEqual(
            email.subject,
            _("We saved your unfinished document: {filename}").format(
                filename=self.email_data.filename
            ),
        )
        self.assertEqual(email.to, [self.email_data.user.email])
