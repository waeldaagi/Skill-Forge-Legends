from django.contrib import admin

from .models import Reply, Report, Thread, Vote

MODERATION_FIELDS = ("moderation_status", "moderation_label", "moderation_confidence")


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "author", *MODERATION_FIELDS, "is_resolved", "created_at")
    list_filter = ("moderation_status", "moderation_label", "is_resolved")
    search_fields = ("title", "content", "author__last_name")
    readonly_fields = ("moderation_job", "created_at", "updated_at")
    list_select_related = ("author",)


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ("thread", "author", *MODERATION_FIELDS, "is_accepted", "created_at")
    list_filter = ("moderation_status", "moderation_label", "is_accepted")
    search_fields = ("content", "author__last_name", "thread__title")
    readonly_fields = ("moderation_job", "created_at", "updated_at")
    list_select_related = ("author", "thread")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("user", "reply", "created_at")
    list_select_related = ("user", "reply__thread")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("reason", "reporter", "thread", "reply", "status", "created_at")
    list_filter = ("status", "reason")
    list_select_related = ("reporter", "thread", "reply")
