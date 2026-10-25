from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SkillForgeUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    # Les groupes découlent du rôle : les éditer à la main ferait diverger rôle et permissions.
    readonly_fields = ("groups", "is_staff", "last_login", "date_joined")
    filter_horizontal = ("user_permissions",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name", "email")}),
        (
            "Rôle et accès",
            {"fields": ("role", "groups", "is_active", "is_staff", "is_superuser")},
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
