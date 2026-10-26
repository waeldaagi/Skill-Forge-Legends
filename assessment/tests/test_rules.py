"""Règles corrigées pendant l'intégration de la Phase 3 (docs/audit/assessment-2026-10-26.md)."""

from unittest import mock

import qrcode
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from assessment.models import AIEvaluation, HumanReview, Submission
from assessment.services import _similarity_score
from assessment.tests.factories import (
    CertificationFactory,
    LearnerFactory,
    MentorFactory,
    TrainerFactory,
    ready_certification,
)
from courses.services import UNVERIFIED_TRAINER_MESSAGE
from courses.tests.factories import CourseFactory


def submission_for(certification, learner=None, status=Submission.Status.EVALUEE_IA, text="preuve"):
    learner = learner or LearnerFactory()
    attempt = Submission.objects.filter(learner=learner, certification=certification).count() + 1
    return Submission.objects.create(
        learner=learner,
        certification=certification,
        text_response=text,
        attempt_number=attempt,
        status=status,
    )


def review_data(decision=HumanReview.Decision.REUSSIE):
    return {
        "final_score": 85,
        "decision": decision,
        "comment": "Preuve solide.",
        "overrides_ai": "",
    }


class AccessTests(TestCase):
    def test_wrong_role_gets_403_instead_of_404(self):
        certification = ready_certification(CertificationFactory())
        submission = submission_for(certification)
        recruiter = UserFactory(role=User.Role.RECRUTEUR)
        self.client.force_login(recruiter)

        for url in (
            reverse("assessment:criterion_create", args=[certification.pk]),
            reverse("assessment:submission_review", args=[submission.pk]),
            reverse("assessment:submission_create", args=[certification.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_administrator_menu_has_no_link_to_the_recruiter_space(self):
        self.client.force_login(UserFactory(role=User.Role.ADMIN))

        labels = [link["label"] for link in self.client.get("/").context["nav_links"]]

        self.assertNotIn("Talents certifiés", labels)


class ReviewTests(TestCase):
    def test_a_decided_submission_cannot_be_reviewed_again(self):
        certification = ready_certification(CertificationFactory())
        submission = submission_for(certification, status=Submission.Status.REUSSIE)
        self.client.force_login(MentorFactory())

        url = reverse("assessment:submission_review", args=[submission.pk])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, review_data("ECHOUEE")).status_code, 404)

    def test_trainer_cannot_review_another_trainers_certification(self):
        certification = ready_certification(CertificationFactory())
        submission = submission_for(certification)
        self.client.force_login(TrainerFactory())

        response = self.client.get(reverse("assessment:submission_review", args=[submission.pk]))

        self.assertEqual(response.status_code, 404)

    def test_review_page_shows_the_proof_to_the_reviewer(self):
        certification = ready_certification(CertificationFactory())
        submission = submission_for(certification, text="Mon API Django est testée à 92 %.")
        self.client.force_login(MentorFactory())

        response = self.client.get(reverse("assessment:submission_review", args=[submission.pk]))

        self.assertContains(response, "Mon API Django est testée à 92 %.")

    def test_certificate_qr_code_points_to_an_absolute_verification_url(self):
        certification = ready_certification(CertificationFactory())
        submission = submission_for(certification)
        self.client.force_login(MentorFactory())

        with mock.patch("assessment.services.qrcode.make", wraps=qrcode.make) as make_qr:
            self.client.post(
                reverse("assessment:submission_review", args=[submission.pk]), review_data()
            )

        certificate = Submission.objects.get(pk=submission.pk).certificate
        make_qr.assert_called_once_with(
            f"http://testserver/certificats/verifier/{certificate.public_id}/"
        )


class FraudTests(TestCase):
    def test_a_learner_improving_their_own_answer_is_not_flagged(self):
        certification = ready_certification(CertificationFactory())
        learner = LearnerFactory()
        text = "J'ai découpé le projet Django en services testés et en vues fines."
        submission_for(certification, learner=learner, text=text)
        retry = submission_for(certification, learner=learner, text=text + " Avec la CI.")

        self.assertLess(_similarity_score(retry), 0.85)

    def test_copying_another_learner_is_still_flagged(self):
        certification = ready_certification(CertificationFactory())
        text = "J'ai découpé le projet Django en services testés et en vues fines."
        submission_for(certification, text=text)
        copy = submission_for(certification, text=text)

        self.assertGreaterEqual(_similarity_score(copy), 0.85)


class CertificationFormTests(TestCase):
    def test_trainer_only_sees_their_own_courses(self):
        trainer = TrainerFactory()
        mine = CourseFactory(trainer=trainer)
        CourseFactory()
        self.client.force_login(trainer)

        response = self.client.get(reverse("assessment:certification_create"))

        self.assertEqual(list(response.context["form"].fields["course"].queryset), [mine])

    def test_unverified_trainer_cannot_activate_a_certification(self):
        trainer = UserFactory(role=User.Role.FORMATEUR, is_verified=False)
        course = CourseFactory(trainer=trainer)
        self.client.force_login(trainer)

        response = self.client.post(
            reverse("assessment:certification_create"),
            {
                "course": course.pk,
                "title": "Django en production",
                "instructions": "Déployez une application testée.",
                "passing_score": 70,
                "max_attempts": 3,
                "is_active": "on",
            },
        )

        self.assertContains(response, UNVERIFIED_TRAINER_MESSAGE)


class CatalogTests(TestCase):
    def test_catalog_asks_to_finish_the_course_before_submitting(self):
        ready_certification(CertificationFactory())
        self.client.force_login(LearnerFactory())

        response = self.client.get(reverse("assessment:certification_catalog"))

        self.assertContains(response, "Terminez tous les chapitres du cours")
        self.assertNotContains(response, "Soumettre une preuve")

    @mock.patch("assessment.views.learner_can_submit", return_value=True)
    def test_catalog_offers_submission_once_the_course_is_finished(self, _can_submit):
        ready_certification(CertificationFactory())
        self.client.force_login(LearnerFactory())

        response = self.client.get(reverse("assessment:certification_catalog"))

        self.assertContains(response, "Soumettre une preuve")


class FeedbackTests(TestCase):
    def test_learner_sees_the_mentor_decision_and_comment(self):
        certification = ready_certification(CertificationFactory())
        submission = submission_for(certification)
        self.client.force_login(MentorFactory())
        self.client.post(
            reverse("assessment:submission_review", args=[submission.pk]), review_data()
        )
        self.client.force_login(submission.learner)

        response = self.client.get(reverse("assessment:submission_detail", args=[submission.pk]))

        self.assertContains(response, "85/100")
        self.assertContains(response, "Preuve solide.")

    def test_review_form_starts_from_the_ai_score(self):
        certification = ready_certification(CertificationFactory())
        submission = submission_for(certification)
        AIEvaluation.objects.create(submission=submission, total_score=73, provider="mock")
        self.client.force_login(MentorFactory())

        response = self.client.get(reverse("assessment:submission_review", args=[submission.pk]))

        self.assertEqual(response.context["form"].initial["final_score"], 73)
