import factory

from accounts.models import User
from accounts.tests.factories import UserFactory
from community.models import ModerationStatus, Reply, Report, Thread, Vote


class ThreadFactory(factory.django.DjangoModelFactory):
    """Fil déjà publié : la plupart des tests partent d'un contenu visible."""

    class Meta:
        model = Thread

    author = factory.SubFactory(UserFactory, role=User.Role.APPRENANT)
    title = factory.Iterator(
        [
            "Migrations en conflit après un merge",
            "select_related ou prefetch_related pour une liste de cours ?",
            "Erreur CSRF avec un formulaire HTMX",
        ]
    )
    content = "J'ai lu la documentation sans comprendre d'où vient le problème. Une piste ?"
    moderation_status = ModerationStatus.APPROUVE


class ReplyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reply

    thread = factory.SubFactory(ThreadFactory)
    author = factory.SubFactory(UserFactory, role=User.Role.APPRENANT)
    content = "Supprime la migration en double, puis lance makemigrations --merge."
    moderation_status = ModerationStatus.APPROUVE


class VoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vote

    user = factory.SubFactory(UserFactory, role=User.Role.APPRENANT)
    reply = factory.SubFactory(ReplyFactory)


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Report

    reporter = factory.SubFactory(UserFactory, role=User.Role.APPRENANT)
    thread = factory.SubFactory(ThreadFactory)
    reason = Report.Reason.SPAM
