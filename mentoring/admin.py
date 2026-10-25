from django.contrib import admin

from .models import AvailabilitySlot, MentoringSession, MentorProfile, SessionReview


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ("mentor", "title", "years_of_experience")
    search_fields = ("mentor__first_name", "mentor__last_name", "mentor__username", "title")
    list_select_related = ("mentor",)


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("mentor", "start", "end", "is_booked")
    list_filter = ("is_booked",)
    search_fields = ("mentor__first_name", "mentor__last_name", "mentor__username")
    date_hierarchy = "start"
    list_select_related = ("mentor",)


@admin.register(MentoringSession)
class MentoringSessionAdmin(admin.ModelAdmin):
    list_display = ("topic", "learner", "slot", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("topic", "learner__last_name", "slot__mentor__last_name")
    readonly_fields = ("room_name", "created_at", "updated_at")
    list_select_related = ("learner", "slot__mentor")


@admin.register(SessionReview)
class SessionReviewAdmin(admin.ModelAdmin):
    list_display = ("session", "rating", "created_at")
    list_filter = ("rating",)
    list_select_related = ("session__slot__mentor",)
