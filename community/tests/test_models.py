from django.db import IntegrityError, transaction
from django.test import TestCase

from community.models import ModerationStatus, Report
from community.tests.factories import ReplyFactory, ReportFactory, ThreadFactory, VoteFactory


class ReportConstraintTests(TestCase):
    def test_report_targeting_a_thread_and_a_reply_is_refused(self):
        reply = ReplyFactory()

        with self.assertRaises(IntegrityError):
            ReportFactory(thread=reply.thread, reply=reply)

    def test_report_targeting_nothing_is_refused(self):
        with self.assertRaises(IntegrityError):
            ReportFactory(thread=None, reply=None)

    def test_report_on_a_reply_is_accepted(self):
        report = ReportFactory(thread=None, reply=ReplyFactory())

        self.assertEqual(report.target, report.reply)


class ReplyConstraintTests(TestCase):
    def test_a_thread_has_at_most_one_accepted_reply(self):
        accepted = ReplyFactory(is_accepted=True)

        with self.assertRaises(IntegrityError), transaction.atomic():
            ReplyFactory(thread=accepted.thread, is_accepted=True)

    def test_a_user_votes_once_per_reply(self):
        vote = VoteFactory()

        with self.assertRaises(IntegrityError):
            VoteFactory(user=vote.user, reply=vote.reply)


class ModeratedContentTests(TestCase):
    def test_author_is_told_where_the_message_stands(self):
        thread = ThreadFactory(moderation_status=ModerationStatus.SIGNALE)

        self.assertIn("masqué", thread.author_message)
        self.assertFalse(thread.is_published)

    def test_reply_text_sent_to_moderation_names_its_thread(self):
        reply = ReplyFactory()

        self.assertIn(reply.thread.title, reply.moderation_text())

    def test_report_str_names_the_reason(self):
        report = ReportFactory(reason=Report.Reason.HORS_SUJET)

        self.assertTrue(str(report).startswith("Hors sujet"))
