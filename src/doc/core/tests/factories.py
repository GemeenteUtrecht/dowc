import factory
import factory.fuzzy

from doc.accounts.tests.factories import UserFactory
from doc.core.constants import DocFileTypes


class DocumentFileFactory(factory.django.DjangoModelFactory):
    purpose = factory.fuzzy.FuzzyChoice(DocFileTypes.values)
    drc_url = factory.Faker("url")
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = "core.DocumentFile"
