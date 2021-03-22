from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from dowc.accounts.tests.factories import UserFactory

from ..email import send_emails
from .factories import EmailDataFactory


class SendEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_send_email_success(self):
        email_data = EmailDataFactory.create()
        result = send_emails([email_data])

        self.assertEqual(result, 1)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.body,
            "Beste {name},\n\n".format(name=email_data.user.username)
            + "Uw openstaande document {filename} is gesloten en de wijzigingen zijn doorgevoerd.\n".format(
                filename=email_data.filename
            )
            + "U kunt uw document vinden als u de volgende link volgt: {info_url}\n\n".format(
                info_url=email_data.info_url
            )
            + "Met vriendelijke groeten,\n\nFunctioneel Beheer Gemeente Utrecht",
        )
        self.assertEqual(
            email.subject,
            _("We saved your unfinished document: {filename}").format(
                filename=email_data.filename
            ),
        )
        self.assertEqual(email.to, [email_data.user.email])

    def test_send_email_no_info_url(self):
        email_data = EmailDataFactory.create(info_url="")
        result = send_emails([email_data])

        self.assertEqual(result, 1)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.body,
            "Beste {name},\n\n".format(name=email_data.user.username)
            + "Uw openstaande document {filename} is gesloten en de wijzigingen zijn doorgevoerd.\n".format(
                filename=email_data.filename
            )
            + "Helaas konden we geen context voor dit document vinden en kunnen u niet naar de oorsprong van het document wijzen.\n\n"
            + "Met vriendelijke groeten,\n\nFunctioneel Beheer Gemeente Utrecht",
        )
        self.assertEqual(
            email.subject,
            _("We saved your unfinished document: {filename}").format(
                filename=email_data.filename
            ),
        )
        self.assertEqual(email.to, [email_data.user.email])

    @patch("dowc.emails.email.logger.warning")
    def test_send_email_user_without_email(self, mock_logger):
        user = UserFactory.create(email="")
        email_data = EmailDataFactory.create(user=user)
        send_emails([email_data])
        mock_logger.assert_called_with(
            f"User with username {user.username} has no known email address."
        )
