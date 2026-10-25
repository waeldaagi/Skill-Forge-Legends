from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class ModerationStatus(models.TextChoices):
    EN_ATTENTE = "EN_ATTENTE", "En attente de vérification"
    APPROUVE = "APPROUVE", "Publié"
    SIGNALE = "SIGNALE", "Masqué, à relire"
    REJETE = "REJETE", "Rejeté"


class ModerationLabel(models.TextChoices):
    OK = "OK", "Conforme"
    SPAM = "SPAM", "Spam"
    TOXIQUE = "TOXIQUE", "Toxique"
    HORS_SUJET = "HORS_SUJET", "Hors sujet"


AUTHOR_MESSAGES = {
    ModerationStatus.EN_ATTENTE: "Votre message attend la vérification d'un modérateur.",
    ModerationStatus.APPROUVE: "Votre message est publié.",
    ModerationStatus.SIGNALE: "Votre message est masqué en attendant la relecture d'un modérateur.",
    ModerationStatus.REJETE: "Votre message a été rejeté par un modérateur.",
}


class ModeratedContent(models.Model):
    """Champs de modération communs aux fils et aux réponses."""

    ModerationStatus = ModerationStatus

    moderation_status = models.CharField(
        "statut de modération",
        max_length=10,
        choices=ModerationStatus.choices,
        default=ModerationStatus.EN_ATTENTE,
        db_index=True,
    )
    moderation_label = models.CharField(
        "étiquette", max_length=10, choices=ModerationLabel.choices, blank=True
    )
    moderation_confidence = models.FloatField(
        "confiance",
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    moderation_reason = models.TextField("motif de modération", blank=True)
    # Dernière vérification lancée : la page de l'auteur en suit le statut en direct.
    moderation_job = models.ForeignKey(
        "core.AIJob", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        abstract = True

    @property
    def is_published(self):
        return self.moderation_status == ModerationStatus.APPROUVE

    @property
    def author_message(self):
        return AUTHOR_MESSAGES[self.moderation_status]


class Thread(ModeratedContent):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="threads",
        verbose_name="auteur",
    )
    title = models.CharField("titre", max_length=150)
    content = models.TextField("message", max_length=5000)
    is_resolved = models.BooleanField("résolu", default=False)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "fil de discussion"
        verbose_name_plural = "fils de discussion"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["moderation_status", "-created_at"])]

    def __str__(self):
        return self.title

    def moderation_text(self):
        return f"Titre : {self.title}\n\n{self.content}"


class Reply(ModeratedContent):
    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name="replies", verbose_name="fil"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_replies",
        verbose_name="auteur",
    )
    content = models.TextField("réponse", max_length=5000)
    is_accepted = models.BooleanField("réponse acceptée", default=False)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        verbose_name = "réponse"
        verbose_name_plural = "réponses"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["thread"],
                condition=Q(is_accepted=True),
                name="one_accepted_reply_per_thread",
            ),
        ]

    def __str__(self):
        return f"Réponse de {self.author} sur « {self.thread} »"

    def moderation_text(self):
        return f"Réponse au sujet « {self.thread.title} » :\n\n{self.content}"


class Vote(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_votes",
        verbose_name="utilisateur",
    )
    reply = models.ForeignKey(
        Reply, on_delete=models.CASCADE, related_name="votes", verbose_name="réponse"
    )
    created_at = models.DateTimeField("voté le", auto_now_add=True)

    class Meta:
        verbose_name = "vote"
        verbose_name_plural = "votes"
        constraints = [
            models.UniqueConstraint(fields=["user", "reply"], name="one_vote_per_user_and_reply"),
        ]

    def __str__(self):
        return f"{self.user} → {self.reply}"


class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM = "SPAM", "Spam ou publicité"
        TOXIQUE = "TOXIQUE", "Propos insultants ou agressifs"
        HORS_SUJET = "HORS_SUJET", "Hors sujet"
        AUTRE = "AUTRE", "Autre motif"

    class Status(models.TextChoices):
        OUVERT = "OUVERT", "À traiter"
        TRAITE = "TRAITE", "Traité"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_reports",
        verbose_name="signalé par",
    )
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name="fil",
    )
    reply = models.ForeignKey(
        Reply,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name="réponse",
    )
    reason = models.CharField("motif", max_length=10, choices=Reason.choices)
    details = models.TextField("précisions", max_length=1000, blank=True)
    status = models.CharField(
        "statut", max_length=10, choices=Status.choices, default=Status.OUVERT
    )
    created_at = models.DateTimeField("signalé le", auto_now_add=True)

    class Meta:
        verbose_name = "signalement"
        verbose_name_plural = "signalements"
        ordering = ["-created_at"]
        constraints = [
            # Un signalement vise un fil ou une réponse, jamais les deux, jamais aucun.
            models.CheckConstraint(
                condition=(
                    Q(thread__isnull=False, reply__isnull=True)
                    | Q(thread__isnull=True, reply__isnull=False)
                ),
                name="report_targets_exactly_one_post",
            ),
        ]

    def __str__(self):
        return f"{self.get_reason_display()} · {self.target}"

    @property
    def target(self):
        return self.thread or self.reply
