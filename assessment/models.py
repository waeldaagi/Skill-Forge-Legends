import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum

from core.validators import validate_upload_size


class Certification(models.Model):
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="certifications",
        verbose_name="cours",
    )
    title = models.CharField("titre", max_length=180)
    instructions = models.TextField("consignes")
    passing_score = models.PositiveSmallIntegerField(
        "score de réussite",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=70,
        help_text="Score minimum sur 100 pour réussir.",
    )
    max_attempts = models.PositiveSmallIntegerField(
        "nombre maximal de tentatives", validators=[MinValueValidator(1)], default=3
    )
    is_active = models.BooleanField("actif", default=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("mise à jour le", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "certification"
        verbose_name_plural = "certifications"
        constraints = [
            models.UniqueConstraint(fields=("course", "title"), name="unique_certification_title")
        ]

    def __str__(self):
        return f"{self.course.title} · {self.title}"

    @property
    def criteria_total(self):
        if self.pk is None:
            return 0
        return self.criteria.aggregate(total=Sum("weight"))["total"] or 0

    def clean(self):
        if self.is_active and self.criteria_total != 100:
            raise ValidationError(
                {"is_active": "Une certification active doit avoir une grille de critères à 100 %."}
            )


class Criterion(models.Model):
    certification = models.ForeignKey(
        Certification,
        on_delete=models.CASCADE,
        related_name="criteria",
        verbose_name="certification",
    )
    name = models.CharField("nom", max_length=120)
    description = models.TextField("description")
    weight = models.PositiveSmallIntegerField(
        "poids", validators=[MinValueValidator(1), MaxValueValidator(100)]
    )

    class Meta:
        ordering = ("id",)
        verbose_name = "critère"
        verbose_name_plural = "critères"
        constraints = [
            models.UniqueConstraint(fields=("certification", "name"), name="unique_criterion_name")
        ]

    def __str__(self):
        return f"{self.certification.title} · {self.name} ({self.weight}%)"

    def clean(self):
        if not self.certification_id:
            return
        siblings_total = (
            self.certification.criteria.exclude(pk=self.pk).aggregate(total=Sum("weight"))["total"]
            or 0
        )
        if siblings_total + self.weight > 100:
            raise ValidationError(
                {"weight": "Le total des poids dépasse 100 %. Ajustez la grille des critères."}
            )


class Submission(models.Model):
    class Status(models.TextChoices):
        SOUMISE = "SOUMISE", "Soumise"
        EVALUATION_IA = "EVALUATION_IA", "Évaluation IA"
        EVALUEE_IA = "EVALUEE_IA", "Évaluée par IA"
        EN_REVUE = "EN_REVUE", "En revue humaine"
        REUSSIE = "REUSSIE", "Réussie"
        ECHOUEE = "ECHOUEE", "Échouée"

    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_submissions",
        verbose_name="apprenant",
        limit_choices_to={"role": "APPRENANT"},
    )
    certification = models.ForeignKey(
        Certification,
        on_delete=models.PROTECT,
        related_name="submissions",
        verbose_name="certification",
    )
    text_response = models.TextField("réponse texte", blank=True)
    repository_url = models.URLField("lien vers dépôt", blank=True)
    attachment = models.FileField(
        "fichier",
        upload_to="assessment/submissions/",
        blank=True,
        validators=[
            FileExtensionValidator(["pdf", "doc", "docx", "txt", "zip", "md"]),
            validate_upload_size,
        ],
    )
    attempt_number = models.PositiveSmallIntegerField("numéro de tentative")
    status = models.CharField(
        "statut", max_length=20, choices=Status.choices, default=Status.SOUMISE
    )
    ai_job = models.ForeignKey(
        "core.AIJob",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assessment_submissions",
        verbose_name="tâche IA",
    )
    created_at = models.DateTimeField("soumise le", auto_now_add=True)
    updated_at = models.DateTimeField("mise à jour le", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "soumission"
        verbose_name_plural = "soumissions"
        constraints = [
            models.UniqueConstraint(
                fields=("learner", "certification", "attempt_number"),
                name="unique_submission_attempt",
            )
        ]

    def __str__(self):
        return f"{self.learner} · {self.certification.title} · tentative {self.attempt_number}"

    def clean(self):
        if not any(
            [self.text_response.strip(), self.repository_url.strip(), bool(self.attachment)]
        ):
            raise ValidationError(
                "Ajoutez au moins une preuve : réponse texte, dépôt ou fichier joint."
            )


class AIEvaluation(models.Model):
    submission = models.OneToOneField(
        Submission,
        on_delete=models.CASCADE,
        related_name="ai_evaluation",
        verbose_name="soumission",
    )
    total_score = models.PositiveSmallIntegerField(
        "score total", validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    criteria_scores = models.JSONField(
        "scores par critère",
        default=dict,
        help_text="Chaque clé contient score et justification.",
    )
    strengths = models.TextField("points forts", blank=True)
    improvement_axes = models.TextField("axes d'amélioration", blank=True)
    confidence = models.FloatField(
        "confiance", validators=[MinValueValidator(0), MaxValueValidator(1)], default=0
    )
    suspected_fraud = models.BooleanField("fraude suspectée", default=False)
    fraud_reasons = models.TextField("raisons de fraude", blank=True)
    provider = models.CharField("fournisseur", max_length=40)
    duration_ms = models.PositiveIntegerField("durée (ms)", default=0)
    created_at = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        verbose_name = "évaluation IA"
        verbose_name_plural = "évaluations IA"

    def __str__(self):
        return f"{self.submission} · {self.total_score}/100"


class HumanReview(models.Model):
    class Decision(models.TextChoices):
        REUSSIE = "REUSSIE", "Réussie"
        ECHOUEE = "ECHOUEE", "Échouée"

    submission = models.OneToOneField(
        Submission,
        on_delete=models.CASCADE,
        related_name="human_review",
        verbose_name="soumission",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_reviews",
        limit_choices_to={"role__in": ["MENTOR", "FORMATEUR"]},
        verbose_name="relecteur",
    )
    final_score = models.PositiveSmallIntegerField(
        "score final", validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    decision = models.CharField("décision", max_length=10, choices=Decision.choices)
    comment = models.TextField("commentaire")
    overrides_ai = models.BooleanField("corrige le score IA", default=False)
    reviewed_at = models.DateTimeField("date de revue", auto_now_add=True)

    class Meta:
        ordering = ("-reviewed_at",)
        verbose_name = "revue humaine"
        verbose_name_plural = "revues humaines"

    def __str__(self):
        return f"{self.submission} · {self.get_decision_display()}"


class Certificate(models.Model):
    public_id = models.UUIDField(
        "identifiant public", default=uuid.uuid4, unique=True, editable=False
    )
    submission = models.OneToOneField(
        Submission,
        on_delete=models.PROTECT,
        related_name="certificate",
        verbose_name="soumission",
    )
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="certificates",
        limit_choices_to={"role": "APPRENANT"},
        verbose_name="apprenant",
    )
    certification = models.ForeignKey(
        Certification,
        on_delete=models.PROTECT,
        related_name="certificates",
        verbose_name="certification",
    )
    issued_at = models.DateTimeField("délivré le", auto_now_add=True)
    pdf = models.FileField("certificat PDF", upload_to="assessment/certificates/")
    is_revoked = models.BooleanField("révoqué", default=False)

    class Meta:
        ordering = ("-issued_at",)
        verbose_name = "certificat"
        verbose_name_plural = "certificats"

    def __str__(self):
        return f"{self.learner} · {self.certification.title}"
