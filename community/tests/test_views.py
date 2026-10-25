from unittest import mock

from django.contrib.messages import get_messages
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from kombu.exceptions import OperationalError

from accounts.models import User
from accounts.tests.factories import UserFactory
from community.models import ModerationStatus, Reply, Report, Thread, Vote
from community.services import HUMAN_REVIEW_REASON
from community.tests.factories import ReplyFactory, ReportFactory, ThreadFactory
from core.ai.jobs import execute_ai_job

Status = ModerationStatus
REDIS_DOWN = OperationalError("Error 10061 connecting to 127.0.0.1:6379.")


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class ThreadListViewTests(TestCase):
    def setUp(self):
        self.learner = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(self.learner)
        self.url = reverse("community:thread_list")

    def test_list_shows_published_threads_and_my_pending_ones(self):
        published = ThreadFactory()
        mine = ThreadFactory(author=self.learner, moderation_status=Status.EN_ATTENTE)
        ThreadFactory(moderation_status=Status.SIGNALE)

        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "community/thread_list.html")
        self.assertCountEqual(response.context["threads"], [published, mine])
        self.assertContains(response, "En attente de vérification")

    def test_search_looks_in_titles_and_messages(self):
        csrf = ThreadFactory(title="Erreur CSRF avec HTMX")
        ThreadFactory(title="Docker compose")

        response = self.client.get(self.url, {"q": "csrf"})

        self.assertEqual(list(response.context["threads"]), [csrf])

    def test_filter_on_resolved_threads(self):
        resolved = ThreadFactory(is_resolved=True)
        ThreadFactory()

        response = self.client.get(self.url, {"resolu": "oui"})

        self.assertEqual(list(response.context["threads"]), [resolved])

    def test_query_count_does_not_grow_with_the_number_of_threads(self):
        ReplyFactory()
        with CaptureQueriesContext(connection) as one_thread:
            self.client.get(self.url)
        for _ in range(5):
            ReplyFactory()

        with CaptureQueriesContext(connection) as six_threads:
            self.client.get(self.url)

        self.assertEqual(len(six_threads), len(one_thread))

    def test_filter_on_threads_without_solution(self):
        open_thread = ThreadFactory()
        ThreadFactory(is_resolved=True)

        response = self.client.get(self.url, {"resolu": "non"})

        self.assertEqual(list(response.context["threads"]), [open_thread])


class ThreadWritingViewTests(TestCase):
    def setUp(self):
        self.learner = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(self.learner)

    def test_new_question_is_checked_then_published(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("community:thread_create"),
                {"title": "Tests de vues", "content": "Comment tester une vue protégée ?"},
            )

        thread = Thread.objects.get()
        self.assertRedirects(response, reverse("community:thread_detail", args=[thread.pk]))
        self.assertEqual(thread.moderation_status, Status.APPROUVE)
        self.assertIn("vérification automatique", messages_of(response)[0])

    def test_author_follows_the_check_live_on_the_thread_page(self):
        with self.captureOnCommitCallbacks(execute=False):
            self.client.post(
                reverse("community:thread_create"),
                {"title": "Tests de vues", "content": "Comment tester une vue protégée ?"},
            )
        thread = Thread.objects.get()

        response = self.client.get(reverse("community:thread_detail", args=[thread.pk]))

        self.assertContains(response, 'role="status"')
        self.assertContains(response, "Vérification automatique de votre message en cours")

    def test_editing_my_thread_sends_it_back_to_moderation(self):
        thread = ThreadFactory(author=self.learner)

        with self.captureOnCommitCallbacks(execute=False):
            self.client.post(
                reverse("community:thread_update", args=[thread.pk]),
                {"title": thread.title, "content": "Version corrigée de ma question."},
            )

        thread.refresh_from_db()
        self.assertEqual(thread.moderation_status, Status.EN_ATTENTE)
        self.assertEqual(thread.content, "Version corrigée de ma question.")

    def test_author_deletes_the_thread_and_its_replies(self):
        thread = ReplyFactory(thread__author=self.learner).thread

        response = self.client.post(reverse("community:thread_delete", args=[thread.pk]))

        self.assertRedirects(response, reverse("community:thread_list"))
        self.assertFalse(Reply.objects.exists())

    def test_author_marks_the_thread_as_resolved(self):
        thread = ThreadFactory(author=self.learner)

        self.client.post(reverse("community:thread_resolve", args=[thread.pk]))

        thread.refresh_from_db()
        self.assertTrue(thread.is_resolved)


class ReplyViewTests(TestCase):
    def setUp(self):
        self.member = UserFactory(role=User.Role.APPRENANT)
        self.client.force_login(self.member)

    def test_reply_is_added_and_the_page_scrolls_to_it(self):
        thread = ThreadFactory()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("community:reply_create", args=[thread.pk]),
                {"content": "Ajoutez app_name dans urls.py."},
            )

        reply = Reply.objects.get()
        self.assertRedirects(
            response,
            f"{reverse('community:thread_detail', args=[thread.pk])}#reponse-{reply.pk}",
            fetch_redirect_response=False,
        )
        self.assertEqual(reply.moderation_status, Status.APPROUVE)

    def test_no_reply_on_my_own_unpublished_thread(self):
        thread = ThreadFactory(author=self.member, moderation_status=Status.EN_ATTENTE)

        response = self.client.post(
            reverse("community:reply_create", args=[thread.pk]), {"content": "Précision."}
        )

        self.assertIn("pas encore publié", messages_of(response)[0])
        self.assertFalse(Reply.objects.exists())

    def test_vote_without_htmx_redirects_to_the_reply(self):
        reply = ReplyFactory()

        self.client.post(reverse("community:reply_vote", args=[reply.pk]))

        self.assertTrue(Vote.objects.filter(user=self.member, reply=reply).exists())

    def test_vote_with_htmx_returns_only_the_updated_button(self):
        reply = ReplyFactory()

        response = self.client.post(
            reverse("community:reply_vote", args=[reply.pk]), headers={"HX-Request": "true"}
        )

        self.assertTemplateUsed(response, "community/partials/vote_button.html")
        self.assertContains(response, 'aria-pressed="true"')
        self.assertContains(response, "(1)")

    def test_voting_for_my_own_reply_is_refused(self):
        reply = ReplyFactory(author=self.member)

        response = self.client.post(
            reverse("community:reply_vote", args=[reply.pk]), headers={"HX-Request": "true"}
        )

        self.assertEqual(response.status_code, 403)

    def test_thread_author_accepts_a_reply(self):
        reply = ReplyFactory(thread__author=self.member)

        response = self.client.post(reverse("community:reply_accept", args=[reply.pk]))

        reply.refresh_from_db()
        self.assertTrue(reply.is_accepted)
        self.assertIn("résolu", messages_of(response)[0])

    def test_author_edits_a_reply_and_it_goes_back_to_moderation(self):
        reply = ReplyFactory(author=self.member)

        with self.captureOnCommitCallbacks(execute=False):
            self.client.post(
                reverse("community:reply_update", args=[reply.pk]), {"content": "Corrigé."}
            )

        reply.refresh_from_db()
        self.assertEqual(reply.moderation_status, Status.EN_ATTENTE)

    def test_member_reports_a_reply_once(self):
        reply = ReplyFactory()
        url = reverse("community:reply_report", args=[reply.pk])

        self.client.post(url, {"reason": Report.Reason.TOXIQUE, "details": ""})
        second = self.client.post(url, {"reason": Report.Reason.TOXIQUE, "details": ""})

        self.assertEqual(Report.objects.filter(reply=reply).count(), 1)
        self.assertIn("déjà signalé", messages_of(second)[-1])

    def test_edit_page_reminds_the_thread(self):
        reply = ReplyFactory(author=self.member)

        response = self.client.get(reverse("community:reply_update", args=[reply.pk]))

        self.assertTemplateUsed(response, "community/reply_form.html")
        self.assertEqual(response.context["thread"], reply.thread)

    def test_author_deletes_a_reply_and_returns_to_the_thread(self):
        reply = ReplyFactory(author=self.member)

        response = self.client.post(reverse("community:reply_delete", args=[reply.pk]))

        self.assertRedirects(response, reverse("community:thread_detail", args=[reply.thread.pk]))
        self.assertFalse(Reply.objects.filter(pk=reply.pk).exists())

    def test_vote_for_my_own_reply_without_htmx_explains_the_refusal(self):
        reply = ReplyFactory(author=self.member)

        response = self.client.post(reverse("community:reply_vote", args=[reply.pk]))

        self.assertIn("propre réponse", messages_of(response)[0])

    def test_reply_with_redis_down_stays_hidden_for_a_human_instead_of_failing(self):
        thread = ThreadFactory()

        with (
            mock.patch.object(execute_ai_job, "apply_async", side_effect=REDIS_DOWN),
            self.assertLogs("core.dispatch", "ERROR"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                reverse("community:reply_create", args=[thread.pk]),
                {"content": "Ajoutez app_name dans urls.py."},
            )

        reply = Reply.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(reply.moderation_status, Status.EN_ATTENTE)
        self.assertEqual(reply.moderation_reason, HUMAN_REVIEW_REASON)


class ModerationQueueViewTests(TestCase):
    def setUp(self):
        self.client.force_login(UserFactory(role=User.Role.MENTOR))

    def test_queue_shows_flagged_messages_with_the_ai_opinion(self):
        ThreadFactory(
            moderation_status=Status.SIGNALE,
            moderation_label="SPAM",
            moderation_confidence=0.93,
            moderation_reason="Lien promotionnel.",
        )

        response = self.client.get(reverse("community:moderation_queue"))

        self.assertTemplateUsed(response, "community/moderation_queue.html")
        self.assertContains(response, "Avis de l'IA")
        self.assertContains(response, "Lien promotionnel.")

    def test_each_rejection_form_has_its_own_field_ids(self):
        first = ThreadFactory(moderation_status=Status.SIGNALE)
        second = ThreadFactory(moderation_status=Status.SIGNALE)

        response = self.client.get(reverse("community:moderation_queue"))

        self.assertContains(response, f'id="rejet-sujet-{first.pk}-reason"', count=1)
        self.assertContains(response, f'id="rejet-sujet-{second.pk}-reason"', count=1)

    def test_moderator_publishes_a_flagged_thread(self):
        thread = ThreadFactory(moderation_status=Status.SIGNALE)

        self.client.post(reverse("community:thread_approve", args=[thread.pk]))

        thread.refresh_from_db()
        self.assertEqual(thread.moderation_status, Status.APPROUVE)

    def test_rejection_requires_a_reason(self):
        thread = ThreadFactory(moderation_status=Status.SIGNALE)

        response = self.client.post(
            reverse("community:thread_reject", args=[thread.pk]), {"reason": ""}
        )

        thread.refresh_from_db()
        self.assertEqual(thread.moderation_status, Status.SIGNALE)
        self.assertIn("motif", messages_of(response)[0])

    def test_rejection_with_a_reason_hides_the_thread(self):
        thread = ThreadFactory(moderation_status=Status.SIGNALE)

        self.client.post(
            reverse("community:thread_reject", args=[thread.pk]), {"reason": "Publicité."}
        )

        thread.refresh_from_db()
        self.assertEqual(thread.moderation_status, Status.REJETE)

    def test_dismissed_report_leaves_the_message_published(self):
        report = ReportFactory()

        self.client.post(reverse("community:report_dismiss", args=[report.pk]))

        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.TRAITE)
        self.assertEqual(report.thread.moderation_status, Status.APPROUVE)
