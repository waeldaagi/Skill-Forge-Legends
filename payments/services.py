"""Logique métier des paiements simulés et des abonnements."""

from datetime import timedelta
from io import BytesIO
from xml.sax.saxutils import escape

from django.db import transaction
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Invoice, Payment, Subscription


def has_active_subscription(user):
    if not user or not user.is_authenticated:
        return False
    return Subscription.objects.filter(
        user=user, status=Subscription.Status.ACTIVE, ends_at__gt=timezone.now()
    ).exists()


@transaction.atomic
def simulate_payment(user, plan, succeeded=True):
    payment = Payment.objects.create(
        user=user,
        plan=plan,
        amount=plan.price,
        status=Payment.Status.SUCCEEDED if succeeded else Payment.Status.FAILED,
    )
    if not succeeded:
        return payment
    now = timezone.now()
    Subscription.objects.create(
        user=user,
        plan=plan,
        starts_at=now,
        ends_at=now + timedelta(days=plan.duration_days),
    )
    invoice = Invoice.objects.create(payment=payment, number=f"SF-{now:%Y%m%d}-{payment.pk:06d}")
    generate_invoice_pdf(invoice)
    return payment


def expire_subscriptions():
    return Subscription.objects.filter(
        status=Subscription.Status.ACTIVE, ends_at__lte=timezone.now()
    ).update(status=Subscription.Status.EXPIRED)


def generate_invoice_pdf(invoice):
    """Génère une facture PDF détaillée et la stocke dans le champ fichier."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    navy = colors.HexColor("#0B1026")
    violet = colors.HexColor("#6D28D9")
    title_style = ParagraphStyle(
        "InvoiceTitle", parent=styles["Title"], textColor=navy, fontSize=24
    )
    subtitle_style = ParagraphStyle(
        "InvoiceSubtitle", parent=styles["Normal"], textColor=violet, fontSize=11
    )
    payment = invoice.payment
    payment_time = timezone.localtime(payment.created_at)
    subscription = (
        Subscription.objects.filter(user=payment.user, plan=payment.plan)
        .order_by("-created_at")
        .first()
    )
    start = timezone.localtime(subscription.starts_at).strftime("%d/%m/%Y %H:%M:%S")
    end = timezone.localtime(subscription.ends_at).strftime("%d/%m/%Y %H:%M:%S")
    details = [
        [Paragraph("Détail", styles["Normal"]), Paragraph("Information", styles["Normal"])],
        ["Numéro de facture", escape(invoice.number)],
        ["Date et heure du paiement", payment_time.strftime("%d/%m/%Y à %H:%M:%S")],
        ["Client", escape(str(payment.user))],
        ["E-mail", escape(payment.user.email or "Non renseigné")],
        ["Offre", escape(payment.plan.name)],
        ["Montant", f"{payment.amount} {payment.currency}"],
        ["Référence", str(payment.reference)],
        ["Fournisseur", escape(payment.provider)],
        ["Statut", escape(payment.get_status_display())],
        ["Abonnement du", start],
        ["Abonnement au", end],
    ]
    story = [
        Paragraph("SkillForge", title_style),
        Paragraph("Facture de souscription", subtitle_style),
        Spacer(1, 14),
        Table(
            details,
            colWidths=[65 * mm, 100 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), navy),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Spacer(1, 18),
        Paragraph("Merci pour votre confiance dans SkillForge.", styles["Normal"]),
    ]
    document.build(story)
    invoice.pdf.save(f"{invoice.number}.pdf", BytesIO(buffer.getvalue()), save=True)
    return invoice
