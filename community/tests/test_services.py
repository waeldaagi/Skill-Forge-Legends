from django.test import TestCase

from accounts.models import User
from accounts.tests.factories import UserFactory
from community import services
from community.models import ModerationStatus, Report, Vote
from community.services import (
    AcceptNotAllowed,
    ReplyNotAllowed,
    ReportNotAllowed,
    VoteNotAllowed,
)
from community.tests.factories import ReplyFactory, ReportFactory, ThreadFactory

Status = ModerationStatus


class VisibilityTests(TestCase):
    def test_others_see_only_published_threads(self):
        published = ThreadFactory()
        ThreadFactory(moderation_status=Status.SIGNALE)
        ThreadFactory(moderation_status=Status.REJETE)

        visible = services.visible_threads(UserFactory())

        self.assertEqual(list(visible), [published])

    def test_authors_also_see_their_own_hidden_threads(self):
        own_pending = ThreadFactory(moderation_status=Status.EN_ATTENTE)

        visible = services.visible_threads(own_pending.author)

        self.assertIn(own_pending, visible)

    def test_reply_count_ignores_hidden_replies(self):
        thread = ThreadFactory()
        ReplyFactory(thread=thread)
        ReplyFactory(thread=thread, moderation_status=Status.SIGNALE)

        listed = services.visible_threads(UserFactory()).get(pk=thread.pk)

        self.assertEqual(listed.reply_count, 1)

    def test_replies_carry_their_vote_count_and_my_vote(self):
        reply = ReplyFactory()
        voter = UserFactory()
        Vote.objects.create(user=voter, reply=reply)

        listed = services.visible_replies(reply.thread, voter).get()

        self.assertEqual(listed.vote_count, 1)
        self.assertTrue(listed.has_voted)

    def test_threads_newest_first_and_replies_oldest_first(self):
        older = ReplyFactory()
        newer_thread = ThreadFactory()
        later_reply = ReplyFactory(thread=older.thread)
        reader = UserFactory()

        self.assertEqual(list(services.visible_threads(reader))[:2], [newer_thread, older.thread])
        self.assertEqual(list(services.visible_replies(older.thread, reader)), [older, later_reply])

    def test_unpublished_thread_accepts_no_reply(self):
        thread = ThreadFactory(moderation_status=Status.EN_ATTENTE)

        with self.assertRaises(ReplyNotAllowed):
            services.create_reply(thread, UserFactory(), "Une réponse")


class ModeratorDecisionTests(TestCase):
    def test_approving_publishes_and_closes_the_reports(self):
        report = ReportFactory(thread__moderation_status=Status.SIGNALE)

        services.approve(report.thread)

        report.refresh_from_db()
        self.assertEqual(report.thread.moderation_status, Status.APPROUVE)
        self.assertEqual(report.status, Report.Status.TRAITE)

    def test_rejecting_keeps_the_reason_for_the_author(self):
        thread = ThreadFactory(moderation_status=Status.SIGNALE)

        services.reject(thread, "Publicité pour une formation payante.")

        self.assertEqual(thread.moderation_status, Status.REJETE)
        self.assertEqual(thread.moderation_reason, "Publicité pour une formation payante.")

    def test_queue_lists_hidden_content_and_open_reports(self):
        flagged = ThreadFactory(moderation_status=Status.SIGNALE)
        ThreadFactory()
        report = ReportFactory()

        queue = services.moderation_queue()

        self.assertEqual(list(queue["threads"]), [flagged])
        self.assertEqual(list(queue["reports"]), [report])


class VoteTests(TestCase):
    def test_second_click_removes_the_vote(self):
        reply = ReplyFactory()
        voter = UserFactory()

        self.assertTrue(services.toggle_vote(voter, reply))
        self.assertFalse(services.toggle_vote(voter, reply))
        self.assertFalse(Vote.objects.exists())

    def test_nobody_votes_for_their_own_reply(self):
        reply = ReplyFactory()

        with self.assertRaises(VoteNotAllowed):
            services.toggle_vote(reply.author, reply)


class AcceptReplyTests(TestCase):
    def test_thread_author_accepts_a_reply_and_the_thread_is_resolved(self):
        reply = ReplyFactory()

        services.accept_reply(reply.thread.author, reply)

        reply.refresh_from_db()
        self.assertTrue(reply.is_accepted)
        self.assertTrue(reply.thread.is_resolved)

    def test_a_mentor_may_accept_a_reply(self):
        reply = ReplyFactory()

        services.accept_reply(UserFactory(role=User.Role.MENTOR), reply)

        reply.refresh_from_db()
        self.assertTrue(reply.is_accepted)

    def test_another_learner_cannot_accept_a_reply(self):
        reply = ReplyFactory()

        with self.assertRaises(AcceptNotAllowed):
            services.accept_reply(UserFactory(role=User.Role.APPRENANT), reply)

    def test_accepting_another_reply_replaces_the_previous_one(self):
        first = ReplyFactory(is_accepted=True)
        second = ReplyFactory(thread=first.thread)

        services.accept_reply(first.thread.author, second)

        first.refresh_from_db()
        self.assertFalse(first.is_accepted)
        self.assertEqual(second.thread.replies.get(is_accepted=True), second)

    def test_hidden_reply_cannot_be_accepted(self):
        reply = ReplyFactory(moderation_status=Status.SIGNALE)

        with self.assertRaises(AcceptNotAllowed):
            services.accept_reply(reply.thread.author, reply)


class ReportTests(TestCase):
    def test_member_reports_a_reply(self):
        reply = ReplyFactory()

        report = services.report_post(UserFactory(), reply, Report.Reason.TOXIQUE, "")

        self.assertEqual(report.reply, reply)
        self.assertEqual(report.status, Report.Status.OUVERT)

    def test_nobody_reports_their_own_message(self):
        thread = ThreadFactory()

        with self.assertRaises(ReportNotAllowed):
            services.report_post(thread.author, thread, Report.Reason.SPAM, "")

    def test_same_member_cannot_report_twice_while_it_is_open(self):
        report = ReportFactory()

        with self.assertRaisesMessage(ReportNotAllowed, "déjà signalé"):
            services.report_post(report.reporter, report.thread, Report.Reason.SPAM, "")
