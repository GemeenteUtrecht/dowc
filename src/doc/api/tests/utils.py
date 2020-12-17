from doc.accounts.tests.factories import UserFactory


class AuthMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory.create()

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)
