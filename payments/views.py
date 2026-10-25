from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, F, IntegerField, OuterRef, Subquery, Value
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView, View

from .models import Invoice, Payment, Plan, Subscription
from .services import generate_invoice_pdf, simulate_payment


class PlanListView(ListView):
    model = Plan
    template_name = "payments/plan_list.html"
    context_object_name = "plans"

    def get_queryset(self):
        plans = Plan.objects.filter(is_active=True)
        if not self.request.user.is_authenticated:
            return plans.annotate(
                active_subscription_id=Value(None, output_field=IntegerField())
            )
        active_subscription = Subscription.objects.filter(
            user=self.request.user,
            plan_id=OuterRef("pk"),
            status=Subscription.Status.ACTIVE,
            ends_at__gt=timezone.now(),
        ).order_by("-ends_at")
        return plans.annotate(active_subscription_id=Subquery(active_subscription.values("pk")[:1]))


class SubscriptionListView(LoginRequiredMixin, ListView):
    model = Subscription
    template_name = "payments/subscription_list.html"
    context_object_name = "subscriptions"

    def get_queryset(self):
        return Subscription.objects.filter(
            user=self.request.user,
            status=Subscription.Status.ACTIVE,
            ends_at__gt=timezone.now(),
        ).select_related("plan")


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = "payments/payment_list.html"
    context_object_name = "payments"

    def get_queryset(self):
        active_subscription = Subscription.objects.filter(
            user=self.request.user,
            plan_id=OuterRef("plan_id"),
            status=Subscription.Status.ACTIVE,
            ends_at__gt=timezone.now(),
        )
        latest_payment = Payment.objects.filter(
            user=self.request.user,
            plan_id=OuterRef("plan_id"),
            status=Payment.Status.SUCCEEDED,
        ).order_by("-created_at", "-pk")
        return (
            Payment.objects.filter(
                user=self.request.user,
                status=Payment.Status.SUCCEEDED,
            )
            .annotate(latest_payment_id=Subquery(latest_payment.values("pk")[:1]))
            .filter(pk=F("latest_payment_id"))
            .filter(Exists(active_subscription))
            .select_related("plan", "invoice")
        )


class CheckoutView(LoginRequiredMixin, View):
    def post(self, request, slug):
        plan = get_object_or_404(Plan, slug=slug, is_active=True)
        already_active = Subscription.objects.filter(
            user=request.user,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            ends_at__gt=timezone.now(),
        ).exists()
        if already_active:
            messages.info(request, "Cet abonnement est déjà actif.")
            return redirect("payments:subscriptions")
        failed = request.POST.get("scenario") == "failure"
        simulate_payment(request.user, plan, succeeded=not failed)
        if failed:
            messages.error(request, "Le paiement de démonstration a échoué.")
        else:
            messages.success(request, "Paiement réussi : votre abonnement est actif.")
        return redirect("payments:subscriptions")


class CancelSubscriptionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
        if subscription.status == Subscription.Status.ACTIVE:
            subscription.status = Subscription.Status.CANCELLED
            subscription.save(update_fields=["status"])
            messages.success(request, "Votre abonnement a été annulé.")
        return redirect("payments:subscriptions")


class InvoiceDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, payment__user=request.user)
        generate_invoice_pdf(invoice)
        return FileResponse(
            invoice.pdf.open("rb"),
            as_attachment=True,
            filename=f"{invoice.number}.pdf",
            content_type="application/pdf",
        )
