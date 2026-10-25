from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Plan(models.Model):
    name = models.CharField("nom", max_length=120)
    slug = models.SlugField("slug", max_length=140, unique=True)
    price = models.DecimalField(
        "prix (TND)",
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )
    duration_days = models.PositiveIntegerField("durée (jours)", validators=[MinValueValidator(1)])
    benefits = models.TextField("avantages", blank=True)
    is_active = models.BooleanField("active", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price", "name"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIREE", "Expirée"
        CANCELLED = "ANNULEE", "Annulée"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    starts_at = models.DateTimeField("débute le")
    ends_at = models.DateTimeField("se termine le")
    status = models.CharField(
        "statut", max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        # Nom fixé par la migration 0001 : sans lui, Django en calcule un autre et réclame
        # une migration de renommage.
        indexes = [
            models.Index(fields=["user", "status", "ends_at"], name="payments_s_user_id_7d7f1f_idx")
        ]

    def __str__(self):
        return f"{self.user} — {self.plan}"

    def clean(self):
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "La fin doit être postérieure au début."})


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "EN_ATTENTE", "En attente"
        SUCCEEDED = "REUSSI", "Réussi"
        FAILED = "ECHOUE", "Échoué"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(
        "montant",
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency = models.CharField("devise", max_length=3, default="TND", editable=False)
    status = models.CharField(
        "statut", max_length=12, choices=Status.choices, default=Status.PENDING
    )
    reference = models.UUIDField("référence", default=uuid4, unique=True, editable=False)
    provider = models.CharField("fournisseur", max_length=30, default="simulation", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.reference)


class Invoice(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="invoice")
    number = models.CharField("numéro", max_length=30, unique=True)
    pdf = models.FileField("facture PDF", upload_to="invoices/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number
