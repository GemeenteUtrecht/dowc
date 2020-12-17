import factory


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@kownsl.nl")

    class Meta:
        model = "accounts.User"
