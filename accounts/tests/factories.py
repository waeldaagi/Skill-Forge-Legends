import factory
from django.utils.text import slugify

from accounts.models import User

DEFAULT_PASSWORD = "Forge-Tunis-2026"

FIRST_NAMES = [
    "Amine",
    "Yasmine",
    "Skander",
    "Mariem",
    "Oussema",
    "Ines",
    "Khalil",
    "Nour",
    "Rania",
    "Hamza",
]
LAST_NAMES = [
    "Ben Salah",
    "Trabelsi",
    "Jaziri",
    "Gharbi",
    "Mejri",
    "Hammami",
    "Chaabane",
    "Ayari",
    "Khelifi",
    "Bouzid",
]


class UserFactory(factory.django.DjangoModelFactory):
    """Utilisateur d'un rôle donné : ``UserFactory(role=User.Role.MENTOR)``."""

    class Meta:
        model = User

    first_name = factory.Iterator(FIRST_NAMES)
    last_name = factory.Iterator(LAST_NAMES)
    username = factory.LazyAttributeSequence(lambda user, n: f"{slugify(user.first_name)}{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@skillforge.test")
    role = User.Role.APPRENANT
    password = factory.django.Password(DEFAULT_PASSWORD)
