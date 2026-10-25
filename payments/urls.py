from django.urls import path

from .views import (
    CancelSubscriptionView,
    CheckoutView,
    InvoiceDownloadView,
    PaymentListView,
    PlanListView,
    SubscriptionListView,
)

app_name = "payments"

urlpatterns = [
    path("", PlanListView.as_view(), name="plans"),
    path("mes-abonnements/", SubscriptionListView.as_view(), name="subscriptions"),
    path("mes-paiements/", PaymentListView.as_view(), name="payments"),
    path("<slug:slug>/payer/", CheckoutView.as_view(), name="checkout"),
    path("abonnement/<int:pk>/annuler/", CancelSubscriptionView.as_view(), name="cancel"),
    path("facture/<int:pk>/telecharger/", InvoiceDownloadView.as_view(), name="invoice_download"),
]
