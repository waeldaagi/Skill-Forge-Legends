from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Etablissement, Skill, User


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Etablissement)
class EtablissementAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "institution_type", "manager", "invite_code")
    list_filter = ("institution_type", "city")
    search_fields = ("name", "city", "invite_code")


@admin.register(User)
class SkillForgeUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_verified",
        "is_active",
    )
    list_filter = ("role", "is_verified", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    # Les groupes découlent du rôle : les éditer à la main ferait diverger rôle et permissions.
    readonly_fields = ("groups", "is_staff", "last_login", "date_joined")
    filter_horizontal = ("user_permissions", "skills")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name", "email", "phone")}),
        (
            "Profil",
            {"fields": ("avatar", "bio", "skills", "is_public_profile", "etablissement")},
        ),
        (
            "Rôle et accès",
            # is_verified : un mentor ou un formateur non vérifié ne peut rien publier.
            {"fields": ("role", "is_verified", "groups", "is_active", "is_staff", "is_superuser")},
        ),
        ("Permissions individuelles", {"fields": ("user_permissions",)}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "role", "password1", "password2"),
            },
        ),
    )
