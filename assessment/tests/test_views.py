from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from assessment.models import Certificate, HumanReview, Submission
from assessment.tests.factories import (
    CertificationFactory,
    LearnerFactory,
    MentorFactory,
    RecruiterFactory,
    TrainerFactory,
    ready_certification,
)


class AssessmentViewTests(TestCase):
    def test_formateur_can_open_criterion_create_page(self):
        trainer = TrainerFactory()
        certification = CertificationFactory(course__trainer=trainer, is_active=False)
        self.client.force_login(trainer)

        response = self.client.get(
            reverse("assessment:criterion_create", kwargs={"certification_pk": certification.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Critère - {certification.title}")

    def test_formateur_can_create_criterion(self):
        trainer = TrainerFactory()
        certification = CertificationFactory(course__trainer=trainer, is_active=False)
        self.client.force_login(trainer)

        response = self.client.post(
            reverse("assessment:criterion_create", kwargs={"certification_pk": certification.pk}),
            {
                "name": "Architecture réseau",
                "description": "Validation de la structure et des choix techniques.",
                "weight": 60,
            },
        )

        self.assertRedirects(
            response,
            reverse("assessment:criterion_create", kwargs={"certification_pk": certification.pk}),
        )
        self.assertTrue(
            certification.criteria.filter(name="Architecture réseau", weight=60).exists()
        )

    def test_formateur_cannot_activate_certification_without_criteria(self):
        trainer = TrainerFactory()
        course = CertificationFactory(course__trainer=trainer).course
        self.client.force_login(trainer)

        response = self.client.post(
            reverse("assessment:certification_create"),
            {
                "course": course.pk,
                "title": "Cisco",
                "instructions": "Il faut le passer !",
                "passing_score": 70,
                "max_attempts": 3,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Une certification active doit avoir une grille de critères à 100 %.",
        )

    @mock.patch("assessment.services.learner_can_submit", return_value=True)
    def test_learner_can_submit_proof(self, _can_submit):
        learner = LearnerFactory()
        certification = ready_certification(CertificationFactory())
        self.client.force_login(learner)

        response = self.client.post(
            reverse("assessment:submission_create", kwargs={"certification_pk": certification.pk}),
            {
                "text_response": "Preuve détaillée",
                "repository_url": "",
            },
        )

        submission = Submission.objects.get(learner=learner, certification=certification)
        self.assertRedirects(
            response, reverse("assessment:submission_detail", kwargs={"pk": submission.pk})
        )

    def test_catalog_shows_certificate_download_when_available(self):
        learner = LearnerFactory()
        certification = ready_certification(CertificationFactory())
        submission = Submission.objects.create(
            learner=learner,
            certification=certification,
            text_response="preuve",
            attempt_number=1,
            status=Submission.Status.REUSSIE,
        )
        certificate = Certificate.objects.create(
            submission=submission,
            learner=learner,
            certification=certification,
            pdf=SimpleUploadedFile("certificate.pdf", b"pdf", content_type="application/pdf"),
            is_revoked=False,
        )
        self.client.force_login(learner)

        response = self.client.get(reverse("assessment:certification_catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Télécharger le certificat")
        self.assertContains(response, certificate.pdf.url)

    def test_recruiter_sees_only_public_profiles(self):
        recruiter = RecruiterFactory()
        public_learner = LearnerFactory(is_public_profile=True)
        private_learner = LearnerFactory(is_public_profile=False)
        certification = ready_certification(CertificationFactory())
        submission = Submission.objects.create(
            learner=public_learner,
            certification=certification,
            text_response="preuve publique",
            attempt_number=1,
            status=Submission.Status.REUSSIE,
        )
        Certificate.objects.create(
            submission=submission,
            learner=public_learner,
            certification=certification,
            pdf=SimpleUploadedFile("certificate.pdf", b"pdf", content_type="application/pdf"),
            is_revoked=False,
        )
        self.client.force_login(recruiter)

        response = self.client.get(reverse("assessment:talent_search"))

        self.assertContains(response, str(public_learner))
        self.assertNotContains(response, str(private_learner))

    def test_formateur_reviews_only_own_certification_submissions(self):
        trainer = TrainerFactory()
        other_trainer = TrainerFactory()
        learner = LearnerFactory()

        own_cert = ready_certification(CertificationFactory(course__trainer=trainer))
        other_cert = ready_certification(CertificationFactory(course__trainer=other_trainer))

        Submission.objects.create(
            learner=learner,
            certification=own_cert,
            text_response="preuve",
            attempt_number=1,
            status=Submission.Status.EVALUEE_IA,
        )
        Submission.objects.create(
            learner=learner,
            certification=other_cert,
            text_response="preuve",
            attempt_number=1,
            status=Submission.Status.EVALUEE_IA,
        )

        self.client.force_login(trainer)
        response = self.client.get(reverse("assessment:review_queue"))

        self.assertContains(response, own_cert.title)
        self.assertNotContains(response, other_cert.title)

    def test_mentor_can_submit_human_review(self):
        mentor = MentorFactory()
        learner = LearnerFactory()
        certification = ready_certification(CertificationFactory())
        submission = Submission.objects.create(
            learner=learner,
            certification=certification,
            text_response="preuve",
            attempt_number=1,
            status=Submission.Status.EVALUEE_IA,
        )

        self.client.force_login(mentor)
        response = self.client.post(
            reverse("assessment:submission_review", kwargs={"pk": submission.pk}),
            {
                "final_score": 80,
                "decision": HumanReview.Decision.REUSSIE,
                "comment": "Correct",
                "overrides_ai": False,
            },
        )

        self.assertRedirects(response, reverse("assessment:review_queue"))
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.REUSSIE)

    def test_recruiter_cannot_open_private_profile_url(self):
        recruiter = RecruiterFactory()
        private_learner = LearnerFactory(is_public_profile=False)
        self.client.force_login(recruiter)

        response = self.client.get(
            reverse("assessment:talent_profile", kwargs={"pk": private_learner.pk})
        )

        self.assertEqual(response.status_code, 404)


class AssessmentPermissionMatrixTests(TestCase):
    def setUp(self):
        self.learner = LearnerFactory()
        self.mentor = MentorFactory()
        self.trainer = TrainerFactory()
        self.recruiter = RecruiterFactory()
        self.certification = ready_certification(CertificationFactory(course__trainer=self.trainer))

    def test_certification_list_reserved_to_formateur(self):
        expected = {
            None: 302,
            User.Role.APPRENANT: 403,
            User.Role.MENTOR: 403,
            User.Role.FORMATEUR: 200,
            User.Role.RECRUTEUR: 403,
            User.Role.ADMIN: 403,
            User.Role.ETABLISSEMENT: 403,
        }
        url = reverse("assessment:certification_list")
        for role, status in expected.items():
            with self.subTest(role=role):
                self.client.logout()
                if role is not None:
                    user = {
                        User.Role.APPRENANT: self.learner,
                        User.Role.MENTOR: self.mentor,
                        User.Role.FORMATEUR: self.trainer,
                        User.Role.RECRUTEUR: self.recruiter,
                        User.Role.ADMIN: LearnerFactory(role=User.Role.ADMIN),
                        User.Role.ETABLISSEMENT: LearnerFactory(role=User.Role.ETABLISSEMENT),
                    }[role]
                    self.client.force_login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, status)
