import factory

from dowc.accounts.tests.factories import UserFactory

from ..data import EmailData


class EmailDataFactory(factory.Factory):
    filename = factory.Faker("file_name")
    info_url = factory.Faker("url")
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = EmailData
