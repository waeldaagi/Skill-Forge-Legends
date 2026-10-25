from django.contrib import admin

from .models import (
    Category,
    Chapter,
    ChapterProgress,
    Choice,
    Course,
    Enrollment,
    Question,
    Quiz,
    QuizAttempt,
    Resource,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "trainer", "level", "status", "is_premium")
    list_filter = ("status", "level", "is_premium", "category")
    search_fields = ("title", "description", "trainer__username")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    list_filter = ("course",)
    search_fields = ("title", "course__title")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "chapter")
    search_fields = ("title", "chapter__title")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("learner", "course", "enrolled_at")
    list_filter = ("course",)
    search_fields = ("learner__username", "course__title")


@admin.register(ChapterProgress)
class ChapterProgressAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "chapter", "completed_at")


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "chapter", "is_ai_generated", "is_published")
    list_filter = ("is_ai_generated", "is_published")
    search_fields = ("title", "chapter__title")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("statement", "quiz", "order")
    search_fields = ("statement", "quiz__title")


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "is_correct")
    list_filter = ("is_correct",)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("learner", "quiz", "score", "completed_at")
    list_filter = ("quiz",)
    search_fields = ("learner__username", "quiz__title")
