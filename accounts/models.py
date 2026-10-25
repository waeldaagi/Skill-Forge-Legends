from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

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
