import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class AICallLog(models.Model):
    """Un appel au fournisseur d'IA.

    Ni prompt, ni réponse, ni utilisateur : le journal ne contient aucune donnée personnelle.
    """

    class ErrorType(models.TextChoices):
        TIMEOUT = "timeout", "Délai dépassé"
        HTTP_ERROR = "http_error", "Erreur HTTP"
        CONNECTION_ERROR = "connection_error", "Service injoignable"
        INVALID_OUTPUT = "invalid_output", "Réponse invalide"

    feature = models.CharField("fonctionnalité", max_length=50)
    provider = models.CharField("fournisseur", max_length=30)
    model_name = models.CharField("modèle", max_length=100, blank=True)
    duration_ms = models.PositiveIntegerField("durée (ms)")
    success = models.BooleanField("succès")
    error_type = models.CharField(
        "type d'erreur", max_length=20, choices=ErrorType.choices, blank=True
    )
    created_at = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "appel IA"
        verbose_name_plural = "appels IA"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["feature", "created_at"])]

    def __str__(self):
        outcome = "succès" if self.success else self.get_error_type_display()
        return f"{self.feature} · {self.provider} · {self.duration_ms} ms · {outcome}"


class AIJob(models.Model):
    """Traitement IA asynchrone : la page en suit le statut pendant que Celery l'exécute."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        RUNNING = "RUNNING", "En cours"
        SUCCEEDED = "SUCCEEDED", "Terminé"
        FAILED = "FAILED", "Échec"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature = models.CharField("fonctionnalité", max_length=50)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_jobs",
        verbose_name="utilisateur",
    )
    status = models.CharField(
        "statut", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    payload = models.JSONField("données d'entrée", default=dict, blank=True)
    result = models.JSONField("résultat", null=True, blank=True)
    error_message = models.TextField("message d'erreur", blank=True)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True, verbose_name="type de cible"
    )
    object_id = models.PositiveBigIntegerField("identifiant de la cible", null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    started_at = models.DateTimeField("démarré le", null=True, blank=True)
    finished_at = models.DateTimeField("terminé le", null=True, blank=True)

    class Meta:
        verbose_name = "tâche IA"
        verbose_name_plural = "tâches IA"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"{self.feature} · {self.get_status_display()}"

    @property
    def is_finished(self):
        return self.status in {self.Status.SUCCEEDED, self.Status.FAILED}

    def mark_running(self):
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_succeeded(self, result):
        self.status = self.Status.SUCCEEDED
        self.result = result
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "result", "finished_at"])

    def mark_failed(self, error_message):
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finished_at"])
