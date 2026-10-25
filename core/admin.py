from django.contrib import admin

from .models import AICallLog, AIJob


class ReadOnlyAdmin(admin.ModelAdmin):
    """Journaux écrits par le code : l'admin les consulte sans pouvoir les modifier."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AICallLog)
class AICallLogAdmin(ReadOnlyAdmin):
    list_display = (
        "created_at",
        "feature",
        "provider",
        "model_name",
        "duration_ms",
        "success",
        "error_type",
    )
    list_filter = ("feature", "provider", "success", "error_type")
    date_hierarchy = "created_at"


@admin.register(AIJob)
class AIJobAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "feature", "user", "status", "finished_at")
    list_filter = ("feature", "status")
    search_fields = ("user__username",)
    list_select_related = ("user",)
