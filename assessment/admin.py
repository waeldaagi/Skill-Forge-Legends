from django.contrib import admin

from . import services
from .models import AIEvaluation, Certificate, Certification, Criterion, HumanReview, Submission


class CriterionInline(admin.TabularInline):
    model = Criterion
    extra = 1


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "passing_score", "max_attempts", "is_active")
    list_filter = ("is_active", "course__category")
    search_fields = ("title", "course__title")
    inlines = [CriterionInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("certification", "learner", "attempt_number", "status", "created_at")
    list_filter = ("status", "certification")
    search_fields = ("learner__username", "learner__email", "certification__title")


@admin.register(AIEvaluation)
class AIEvaluationAdmin(admin.ModelAdmin):
    list_display = ("submission", "total_score", "confidence", "suspected_fraud", "provider")
    list_filter = ("suspected_fraud", "provider")
    search_fields = ("submission__learner__username", "submission__certification__title")


@admin.register(HumanReview)
class HumanReviewAdmin(admin.ModelAdmin):
    list_display = ("submission", "reviewer", "final_score", "decision", "overrides_ai")
    list_filter = ("decision", "overrides_ai")
    search_fields = ("submission__learner__username", "reviewer__username")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("public_id", "learner", "certification", "issued_at", "is_revoked")
    list_filter = ("is_revoked", "certification")
    search_fields = ("learner__username", "public_id")
    actions = ["revoke_selected"]

    @admin.action(description="Révoquer les certificats sélectionnés")
    def revoke_selected(self, request, queryset):
        for certificate in queryset:
            services.revoke_certificate(certificate)
