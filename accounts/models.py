from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import FileExtensionValidator
from django.db import models

from core.validators import validate_upload_size

from .services import assign_role_group


class SkillForgeUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Sans cela, « createsuperuser » produirait un apprenant (rôle par défaut).
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        APPRENANT = "APPRENANT", "Apprenant"
        MENTOR = "MENTOR", "Mentor"
        FORMATEUR = "FORMATEUR", "Formateur"
        RECRUTEUR = "RECRUTEUR", "Recruteur"
        ADMIN = "ADMIN", "Administrateur"
        ETABLISSEMENT = "ETABLISSEMENT", "Établissement"

    role = models.CharField("rôle", max_length=20, choices=Role.choices, default=Role.APPRENANT)
    avatar = models.ImageField(
        "avatar",
        upload_to="avatars/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_upload_size],
    )
    bio = models.TextField("biographie", blank=True, max_length=1000)
    phone = models.CharField("téléphone", blank=True, max_length=30)
    skills = models.ManyToManyField(
        "Skill", blank=True, related_name="users", verbose_name="compétences"
    )
    is_public_profile = models.BooleanField("profil public", default=False)
    is_verified = models.BooleanField("profil vérifié", default=False)
    etablissement = models.ForeignKey(
        "Etablissement",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="learners",
        verbose_name="établissement",
    )

    objects = SkillForgeUserManager()

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return self.get_full_name() or self.username

    @classmethod
    def from_db(cls, db, field_names, values):
        user = super().from_db(db, field_names, values)
        # Rôle tel qu'en base : save() ne resynchronise les groupes que s'il a changé.
        user._saved_role = user.__dict__.get("role")
        return user

    def save(self, *args, **kwargs):
        # L'admin Django est réservé aux administrateurs ; les autres rôles passent par l'interface.
        self.is_staff = self.is_superuser or self.role == self.Role.ADMIN
        super().save(*args, **kwargs)
        if self.role != getattr(self, "_saved_role", None):
            assign_role_group(self)
            self._saved_role = self.role


class Skill(models.Model):
    name = models.CharField("nom", max_length=80, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "compétence"
        verbose_name_plural = "compétences"

    def __str__(self):
        return self.name


class Etablissement(models.Model):
    class InstitutionType(models.TextChoices):
        UNIVERSITY = "UNIVERSITY", "Université"
        SCHOOL = "SCHOOL", "École"
        TRAINING_CENTER = "TRAINING_CENTER", "Centre de formation"

    name = models.CharField("nom", max_length=150)
    city = models.CharField("ville", max_length=80)
    institution_type = models.CharField(
        "type", max_length=20, choices=InstitutionType.choices, default=InstitutionType.SCHOOL
    )
    logo = models.ImageField(
        "logo",
        upload_to="institutions/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_upload_size],
    )
    invite_code = models.CharField("code d'invitation", max_length=16, unique=True, editable=False)
    manager = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="managed_institution",
        limit_choices_to={"role": User.Role.ETABLISSEMENT},
        verbose_name="responsable",
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "établissement"
        verbose_name_plural = "établissements"

    def __str__(self):
        return f"{self.name} ({self.city})"

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = self._generate_invite_code()
        super().save(*args, **kwargs)

    def _generate_invite_code(self):
        from secrets import token_urlsafe

        code = token_urlsafe(8).upper()[:12]
        while type(self).objects.filter(invite_code=code).exists():
            code = token_urlsafe(8).upper()[:12]
        return code
