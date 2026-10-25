from django.contrib import admin

from .models import Invoice, Payment, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "starts_at", "ends_at")
    list_filter = ("status", "plan")
    search_fields = ("user__username", "user__email")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "plan", "amount", "status", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("user__username", "reference")
    readonly_fields = ("reference", "provider", "currency")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "payment", "created_at")
    search_fields = ("number",)
    readonly_fields = ("number", "payment")
