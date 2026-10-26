from io import BytesIO

import qrcode
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.ai import run_ai_job
from core.services import queue_email

from .models import AIEvaluation, Certificate, HumanReview, Submission

SIMILARITY_THRESHOLD = 0.85


def verified_certificates(user):
    return Certificate.objects.filter(learner=user, is_revoked=False).select_related(
        "certification"
    )


def certification_ready(certification):
    return certification.criteria_total == 100 and certification.is_active


def learner_can_submit(learner, certification):
    from courses.services import is_course_completed

    return is_course_completed(learner, certification.course)


def next_attempt_number(learner, certification):
    last = (
        Submission.objects.filter(learner=learner, certification=certification)
        .order_by("-attempt_number")
        .first()
    )
    return (last.attempt_number if last else 0) + 1


@transaction.atomic
def submit_submission(learner, certification, text_response="", repository_url="", attachment=None):
    if not certification_ready(certification):
        raise ValidationError("La certification n'est pas prête : la grille doit totaliser 100 %.")
    if not learner_can_submit(learner, certification):
        raise PermissionDenied(
            "Vous devez d'abord terminer le cours pour soumettre cette certification."
        )

    attempt_number = next_attempt_number(learner, certification)
    if attempt_number > certification.max_attempts:
        raise ValidationError("Nombre maximal de tentatives atteint pour cette certification.")

    submission = Submission(
        learner=learner,
        certification=certification,
        text_response=text_response,
        repository_url=repository_url,
        attachment=attachment,
        attempt_number=attempt_number,
        status=Submission.Status.SOUMISE,
    )
    submission.full_clean()
    submission.save()
    request_ai_evaluation(submission)
    return submission


@transaction.atomic
def request_ai_evaluation(submission):
    submission.status = Submission.Status.EVALUATION_IA
    submission.ai_job = run_ai_job("assessment_evaluation", submission.learner, target=submission)
    submission.save(update_fields=["status", "ai_job", "updated_at"])


def _similarity_score(submission):
    if not submission.text_response.strip():
        return 0.0

    previous = list(
        Submission.objects.filter(certification=submission.certification)
        .exclude(pk=submission.pk)
        .values_list("text_response", flat=True)
    )
    previous = [text.strip() for text in previous if text and text.strip()]
    if not previous:
        return 0.0

    corpus = [submission.text_response.strip(), *previous]
    vectors = TfidfVectorizer().fit_transform(corpus)
    scores = cosine_similarity(vectors[0:1], vectors[1:]).flatten()
    return float(scores.max()) if len(scores) else 0.0


@transaction.atomic
def apply_ai_evaluation(submission, result, provider, duration_ms):
    similarity = _similarity_score(submission)
    ai_fraud = bool(result.get("suspected_fraud", False))
    reasons = list(result.get("fraud_reasons", []))

    if similarity >= SIMILARITY_THRESHOLD:
        reasons.append(
            f"Similarité TF-IDF élevée avec des soumissions précédentes ({similarity * 100:.1f}%)."
        )

    suspected_fraud = ai_fraud or similarity >= SIMILARITY_THRESHOLD
    evaluation, _ = AIEvaluation.objects.update_or_create(
        submission=submission,
        defaults={
            "total_score": int(result.get("total_score", 0)),
            "criteria_scores": result.get("criteria_scores", {}),
            "strengths": "\n".join(result.get("strengths", [])),
            "improvement_axes": "\n".join(result.get("improvement_axes", [])),
            "confidence": float(result.get("confidence", 0)),
            "suspected_fraud": suspected_fraud,
            "fraud_reasons": "\n".join(reasons),
            "provider": provider,
            "duration_ms": int(duration_ms),
        },
    )

    submission.status = Submission.Status.EVALUEE_IA
    submission.save(update_fields=["status", "updated_at"])
    return evaluation


@transaction.atomic
def keep_for_human_review(submission):
    AIEvaluation.objects.update_or_create(
        submission=submission,
        defaults={
            "total_score": 0,
            "criteria_scores": {},
            "strengths": "",
            "improvement_axes": "Évaluation IA indisponible. Revue humaine obligatoire.",
            "confidence": 0,
            "suspected_fraud": True,
            "fraud_reasons": "Échec de l'évaluation IA.",
            "provider": "unavailable",
            "duration_ms": 0,
        },
    )
    submission.status = Submission.Status.EN_REVUE
    submission.save(update_fields=["status", "updated_at"])


@transaction.atomic
def finalize_human_review(submission, reviewer, final_score, decision, comment, overrides_ai):
    review, _ = HumanReview.objects.update_or_create(
        submission=submission,
        defaults={
            "reviewer": reviewer,
            "final_score": final_score,
            "decision": decision,
            "comment": comment,
            "overrides_ai": overrides_ai,
        },
    )

    submission.status = (
        Submission.Status.REUSSIE
        if decision == HumanReview.Decision.REUSSIE
        else Submission.Status.ECHOUEE
    )
    submission.save(update_fields=["status", "updated_at"])

    certificate = None
    if decision == HumanReview.Decision.REUSSIE:
        certificate = issue_certificate(submission)
    return review, certificate


@transaction.atomic
def issue_certificate(submission):
    certificate, created = Certificate.objects.get_or_create(
        submission=submission,
        defaults={
            "learner": submission.learner,
            "certification": submission.certification,
            "pdf": "",
        },
    )
    if created or not certificate.pdf:
        pdf_bytes = generate_certificate_pdf(certificate)
        certificate.pdf.save(
            f"certificate-{certificate.public_id}.pdf",
            ContentFile(pdf_bytes),
            save=True,
        )
    return certificate


def generate_certificate_pdf(certificate):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setTitle("Certificat SkillForge")

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(70, 790, "SkillForge - Certificat de réussite")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(70, 740, f"Apprenant : {certificate.learner}")
    pdf.drawString(70, 720, f"Certification : {certificate.certification.title}")
    pdf.drawString(70, 700, f"Date : {timezone.localdate().isoformat()}")
    pdf.drawString(70, 680, f"Identifiant : {certificate.public_id}")

    verify_url = f"/certificats/verifier/{certificate.public_id}/"
    api_url = f"/api/certificats/{certificate.public_id}/"
    qr = qrcode.make(api_url)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    pdf.drawImage(ImageReader(qr_buffer), 70, 520, width=120, height=120)
    pdf.drawString(200, 610, "Scanner le QR code pour vérifier le certificat.")
    pdf.drawString(200, 592, f"Vérification : {verify_url}")
    pdf.drawString(200, 574, f"API : {api_url}")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@transaction.atomic
def revoke_certificate(certificate):
    certificate.is_revoked = True
    certificate.save(update_fields=["is_revoked"])


def recruiter_candidates(query="", skill=None, certification=None):
    from accounts.models import User

    learners = User.objects.filter(
        role=User.Role.APPRENANT,
        is_public_profile=True,
        certificates__is_revoked=False,
    ).distinct()
    if query:
        learners = learners.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
            | Q(skills__name__icontains=query)
        )
    if skill:
        learners = learners.filter(skills=skill)
    if certification:
        learners = learners.filter(certificates__certification=certification)
    return learners.prefetch_related("skills", "certificates__certification")


def contact_candidate(recruiter, learner, subject, message):
    prefixed = f"Message de {recruiter} (recruteur SkillForge)\n\n{message}"
    queue_email(subject, prefixed, [learner.email])
