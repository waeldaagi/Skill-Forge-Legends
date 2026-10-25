"""Matrice d'accès du forum : chaque URL, pour chaque rôle et pour un visiteur anonyme.

Les utilisateurs de la matrice ne sont auteurs d'aucun contenu : un rôle autorisé reçoit 404 sur
le message d'un autre ou sur un sujet non publié. docs/modules/community.md reprend ces règles.
"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from community.models import ModerationStatus
from community.tests.factories import ReplyFactory, ReportFactory, ThreadFactory

ANONYMOUS = None
Role = User.Role
FORUM = {Role.APPRENANT, Role.MENTOR, Role.FORMATEUR, Role.ADMIN}
MODERATORS = {Role.MENTOR, Role.ADMIN}


def expected(allowed_roles, allowed_status=200):
    statuses = {ANONYMOUS: 302}
    for role in Role:
        statuses[role] = allowed_status if role in allowed_roles else 403
    return statuses


class CommunityAccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reply = ReplyFactory()
        cls.thread = cls.reply.thread
        cls.pending_thread = ThreadFactory(moderation_status=ModerationStatus.EN_ATTENTE)
        cls.users = {role: UserFactory(role=role) for role in Role}

    def check(self, url, statuses, method="get"):
        """url : chaîne, ou fonction sans argument quand chaque appel doit viser un objet neuf."""
        for role, status in statuses.items():
            with self.subTest(url=url, role=role):
                self.client.logout()
                if role is not ANONYMOUS:
                    self.client.force_login(self.users[role])
                target = url() if callable(url) else url
                response = getattr(self.client, method)(target)
                self.assertEqual(response.status_code, status)

    def test_forum_pages_are_open_to_learners_mentors_trainers_and_admins(self):
        forum = expected(FORUM)
        self.check(reverse("community:thread_list"), forum)
        self.check(reverse("community:thread_create"), forum)
        self.check(reverse("community:thread_detail", args=[self.thread.pk]), forum)
        self.check(reverse("community:reply_create", args=[self.thread.pk]), forum)
        self.check(reverse("community:thread_report", args=[self.thread.pk]), forum)
        self.check(reverse("community:reply_report", args=[self.reply.pk]), forum)

    def test_unpublished_thread_of_someone_else_is_not_found(self):
        not_found = expected(FORUM, allowed_status=404)
        self.check(reverse("community:thread_detail", args=[self.pending_thread.pk]), not_found)
        self.check(reverse("community:reply_create", args=[self.pending_thread.pk]), not_found)

    def test_only_the_author_edits_or_deletes_a_message(self):
        not_found = expected(FORUM, allowed_status=404)
        self.check(reverse("community:thread_update", args=[self.thread.pk]), not_found)
        self.check(reverse("community:thread_delete", args=[self.thread.pk]), not_found)
        self.check(
            reverse("community:thread_resolve", args=[self.thread.pk]), not_found, method="post"
        )
        self.check(reverse("community:reply_update", args=[self.reply.pk]), not_found)
        self.check(reverse("community:reply_delete", args=[self.reply.pk]), not_found)

    def test_votes_and_acceptance_answer_with_a_redirect(self):
        redirect = expected(FORUM, allowed_status=302)
        self.check(reverse("community:reply_vote", args=[self.reply.pk]), redirect, method="post")
        self.check(reverse("community:reply_accept", args=[self.reply.pk]), redirect, method="post")

    def test_moderation_is_reserved_to_mentors_and_admins(self):
        self.check(reverse("community:moderation_queue"), expected(MODERATORS))
        decision = expected(MODERATORS, allowed_status=302)
        self.check(
            reverse("community:thread_approve", args=[self.pending_thread.pk]),
            decision,
            method="post",
        )
        self.check(reverse("community:reply_reject", args=[self.reply.pk]), decision, method="post")
        self.check(
            lambda: reverse("community:report_dismiss", args=[ReportFactory().pk]),
            decision,
            method="post",
        )
