import factory
import factory.fuzzy

from dowc.accounts.tests.factories import UserFactory
from dowc.core.constants import DocFileTypes


class DocumentFileFactory(factory.django.DjangoModelFactory):
    purpose = factory.fuzzy.FuzzyChoice(DocFileTypes.values)
    drc_url = factory.Faker("url")
    user = factory.SubFactory(UserFactory)
    safe_for_deletion = False
    info_url = factory.Faker("url")

    class Meta:
        model = "core.DocumentFile"
