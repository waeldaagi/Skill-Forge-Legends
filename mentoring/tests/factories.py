from datetime import timedelta

import factory
from django.utils import timezone

from accounts.models import User
from accounts.tests.factories import UserFactory
from mentoring.models import AvailabilitySlot, MentoringSession, MentorProfile, SessionReview


def in_days(days, hour=14):
    """Date future à heure fixe, pour des créneaux lisibles dans les tests."""
    moment = timezone.localtime() + timedelta(days=days)
    return moment.replace(hour=hour, minute=0, second=0, microsecond=0)


class MentorProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MentorProfile

    mentor = factory.SubFactory(UserFactory, role=User.Role.MENTOR, is_verified=True)
    title = factory.Iterator(
        [
            "Développeur back-end Django",
            "Ingénieure DevOps, Docker et CI",
            "Développeur front-end, accessibilité web",
        ]
    )
    years_of_experience = 6


class AvailabilitySlotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AvailabilitySlot

    mentor = factory.SubFactory(UserFactory, role=User.Role.MENTOR, is_verified=True)
    start = factory.LazyFunction(lambda: in_days(3))
    end = factory.LazyAttribute(lambda slot: slot.start + timedelta(hours=1))


class MentoringSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MentoringSession

    slot = factory.SubFactory(AvailabilitySlotFactory, is_booked=True)
    learner = factory.SubFactory(UserFactory, role=User.Role.APPRENANT)
    topic = "Erreur NoReverseMatch sur une URL avec namespace"
    blocker_description = (
        "Mon template appelle {% url 'courses:detail' %} et Django lève NoReverseMatch. "
        "J'ai vérifié app_name dans urls.py sans trouver la cause."
    )


class SessionReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SessionReview

    session = factory.SubFactory(MentoringSessionFactory, status=MentoringSession.Status.TERMINEE)
    rating = 5
    comment = "Explications claires, le problème venait du include sans namespace."
