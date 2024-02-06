import factory


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@dowc.nl")
    password = factory.PostGenerationMethodCall("set_password", "secret")

    class Meta:
        model = "accounts.User"


class ApplicationTokenFactory(factory.django.DjangoModelFactory):
    contact_person = factory.Faker("name")
    email = factory.Faker("email")

    class Meta:
        model = "accounts.ApplicationToken"
