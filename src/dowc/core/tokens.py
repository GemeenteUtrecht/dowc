from datetime import date

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36

from dowc.accounts.models import User


class DocumentTokenGenerator:
    """
    Strategy object used to generate and check tokens for the password
    reset mechanism.

    This is NOT a single use token generator (yet).
    """

    key_salt = "doc.core.tokens.DocumentTokenGenerator"
    secret = settings.SECRET_KEY

    def make_token(self, user: User, uuid: str) -> str:
        """
        Return a token that can be used once to open a document.
        """
        return self._make_token_with_timestamp(
            user, self._num_days(self._today()), uuid
        )

    def check_token(self, user: User, uuid: str, token: str) -> bool:
        """
        Check that a document token is correct for a given user and uuid.
        """
        if not (user and uuid and token):
            return False

        # Parse the token
        try:
            ts_b36, _ = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(
            self._make_token_with_timestamp(user, ts, uuid), token
        ):
            return False

        # Check the timestamp is within limit. Timestamps are rounded to
        # midnight (server time) providing a resolution of only 1 day. If a
        # link is generated 5 minutes before midnight and used 6 minutes later,
        # that counts as 1 day. Therefore, DOCUMENT_TOKEN_TIMEOUT_DAYS = 1 means
        # "at least 1 day, could be up to 2."
        if (self._num_days(self._today()) - ts) > settings.DOCUMENT_TOKEN_TIMEOUT_DAYS:
            return False

        return True

    def _make_token_with_timestamp(self, user: User, timestamp: int, uuid: str) -> str:
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(user, timestamp, uuid),
            secret=self.secret,
        ).hexdigest()[
            ::2
        ]  # Limit to 20 characters to shorten the URL.
        return "%s-%s" % (ts_b36, hash_string)

    def _make_hash_value(self, user: User, timestamp: int, uuid: str) -> str:
        """
        Hash the:
            user primary key and password,
            documentfile uuid, and
            timestamp.

        Failing those things, settings.DOCUMENT_TOKEN_TIMEOUT_DAYS eventually
        invalidates the token.
        """
        return str(user.pk) + user.password + str(timestamp) + str(uuid)

    def _num_days(self, dt) -> int:
        return (dt - date(2001, 1, 1)).days

    def _today(self) -> date:
        # Used for mocking in tests
        return date.today()


document_token_generator = DocumentTokenGenerator()
