import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.formats import date_format

from accounts.models import User

MIN_SLOT_DURATION = timedelta(minutes=30)
MAX_SLOT_DURATION = timedelta(minutes=120)
JITSI_BASE_URL = "https://meet.jit.si"
# Formats Django : « mardi 28 octobre 2026, 14 h 00 » ; \h est un « h » littéral. Les espaces
# autour du « h » sont insécables : l'heure n'est jamais coupée en fin de ligne.
TIME_FORMAT = "G \\h i"
DAY_AND_TIME_FORMAT = f"l j F Y, {TIME_FORMAT}"


def format_period(start, end):
    """Période d'un créneau à l'heure de Tunis : « mardi 28 octobre 2026, 14 h 00 – 15 h 00 »."""
    start, end = timezone.localtime(start), timezone.localtime(end)
    return f"{date_format(start, DAY_AND_TIME_FORMAT)} – {date_format(end, TIME_FORMAT)}"


class MentorProfile(models.Model):
    mentor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentor_profile",
        limit_choices_to={"role": User.Role.MENTOR},
        verbose_name="mentor",
    )
    title = models.CharField(
        "titre",
        max_length=120,
        help_text="Votre spécialité en une ligne, par exemple « Développeur back-end Django ».",
    )
    years_of_experience = models.PositiveSmallIntegerField(
        "années d'expérience", validators=[MaxValueValidator(50)]
    )
    expertises = models.ManyToManyField(
        "accounts.Skill", blank=True, related_name="mentor_profiles", verbose_name="expertises"
    )

    class Meta:
        verbose_name = "profil de mentor"
        verbose_name_plural = "profils de mentor"
        ordering = ["mentor__last_name", "mentor__first_name"]

    def __str__(self):
        return f"{self.mentor} · {self.title}"

    def clean(self):
        if self.mentor_id and self.mentor.role != User.Role.MENTOR:
            raise ValidationError(
                {"mentor": "Seul un utilisateur au rôle Mentor peut avoir un profil de mentor."}
            )


class AvailabilitySlot(models.Model):
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_slots",
        limit_choices_to={"role": User.Role.MENTOR},
        verbose_name="mentor",
    )
    start = models.DateTimeField("début")
    end = models.DateTimeField("fin")
    is_booked = models.BooleanField("réservé", default=False)

    class Meta:
        verbose_name = "créneau"
        verbose_name_plural = "créneaux"
        ordering = ["start"]
        constraints = [
            models.CheckConstraint(condition=Q(end__gt=F("start")), name="slot_end_after_start"),
        ]
        indexes = [models.Index(fields=["mentor", "start"])]

    def __str__(self):
        return f"{self.mentor} · {format_period(self.start, self.end)}"

    def clean(self):
        # Champ invalide : son erreur est déjà affichée par le formulaire.
        if self.start is None or self.end is None:
            return
        if self.end <= self.start:
            raise ValidationError({"end": "La fin du créneau doit être après son début."})
        if self.start <= timezone.now():
            raise ValidationError({"start": "Le créneau doit commencer dans le futur."})
        if not MIN_SLOT_DURATION <= self.end - self.start <= MAX_SLOT_DURATION:
            raise ValidationError({"end": "Un créneau dure entre 30 et 120 minutes."})
        if self.mentor_id and self.overlapping_slots().exists():
            raise ValidationError("Ce créneau chevauche un autre de vos créneaux.")

    @property
    def period(self):
        return format_period(self.start, self.end)

    def overlapping_slots(self):
        return AvailabilitySlot.objects.filter(
            mentor_id=self.mentor_id, start__lt=self.end, end__gt=self.start
        ).exclude(pk=self.pk)


class SessionStatus(models.TextChoices):
    DEMANDEE = "DEMANDEE", "Demandée"
    CONFIRMEE = "CONFIRMEE", "Confirmée"
    TERMINEE = "TERMINEE", "Terminée"
    ANNULEE = "ANNULEE", "Annulée"
    REFUSEE = "REFUSEE", "Refusée"


# Une session annulée ou refusée libère son créneau : elle ne compte plus comme réservation.
ACTIVE_SESSION_STATUSES = [SessionStatus.DEMANDEE, SessionStatus.CONFIRMEE, SessionStatus.TERMINEE]


class MentoringSession(models.Model):
    Status = SessionStatus

    slot = models.ForeignKey(
        AvailabilitySlot, on_delete=models.PROTECT, related_name="sessions", verbose_name="créneau"
    )
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentoring_sessions",
        limit_choices_to={"role": User.Role.APPRENANT},
        verbose_name="apprenant",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentoring_sessions",
        verbose_name="cours concerné",
    )
    topic = models.CharField("sujet", max_length=150)
    blocker_description = models.TextField("description du blocage", max_length=2000)
    status = models.CharField(
        "statut", max_length=10, choices=SessionStatus.choices, default=SessionStatus.DEMANDEE
    )
    room_name = models.UUIDField("salle", default=uuid.uuid4, unique=True, editable=False)
    mentor_notes = models.TextField("notes du mentor", max_length=2000, blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        verbose_name = "session de mentorat"
        verbose_name_plural = "sessions de mentorat"
        ordering = ["-slot__start"]
        constraints = [
            # Seconde barrière contre la double réservation, au niveau de la base de données.
            models.UniqueConstraint(
                fields=["slot"],
                condition=Q(status__in=ACTIVE_SESSION_STATUSES),
                name="one_active_session_per_slot",
            ),
        ]

    def __str__(self):
        return f"{self.topic} · {self.slot}"

    @property
    def mentor(self):
        return self.slot.mentor

    @property
    def jitsi_url(self):
        return f"{JITSI_BASE_URL}/SkillForge-{self.room_name}"


class SessionReview(models.Model):
    session = models.OneToOneField(
        MentoringSession, on_delete=models.CASCADE, related_name="review", verbose_name="session"
    )
    rating = models.PositiveSmallIntegerField(
        "note", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField("commentaire", max_length=1000, blank=True)
    created_at = models.DateTimeField("donné le", auto_now_add=True)

    class Meta:
        verbose_name = "avis de session"
        verbose_name_plural = "avis de session"
        constraints = [
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5), name="review_rating_between_1_and_5"
            ),
        ]

    def __str__(self):
        return f"{self.rating}/5 · {self.session.topic}"
