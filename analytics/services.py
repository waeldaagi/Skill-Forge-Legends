import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone

from core.models import AICallLog
from payments.models import Payment, Subscription


def dropout_summary():
    """Return the latest synthetic dropout training summary for the dashboard."""
    metrics_path = Path(settings.BASE_DIR) / "analytics" / "artifacts" / "dropout_metrics.json"
    dataset_path = Path(settings.BASE_DIR) / "analytics" / "fixtures" / "dropout_dataset.json"
    if not metrics_path.exists() or not dataset_path.exists():
        return {
            "available": False,
            "dataset_size": 0,
            "dropout_rate": 0,
            "best_model": "-",
            "f1": 0,
        }

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    dropout_count = sum(row.get("dropout", 0) for row in dataset)
    best_model = metrics["best_model"]
    return {
        "available": True,
        "dataset_size": len(dataset),
        "dropout_rate": round(dropout_count / len(dataset) * 100, 2) if dataset else 0,
        "best_model": best_model,
        "f1": metrics["models"][best_model]["f1"],
    }


def dashboard_metrics(user):
    """Calcule des indicateurs en lecture seule à partir des données existantes."""
    now = timezone.now()
    active_subscriptions = Subscription.objects.filter(
        user=user, status=Subscription.Status.ACTIVE, ends_at__gt=now
    )
    successful_payments = Payment.objects.filter(
        user=user, status=Payment.Status.SUCCEEDED
    )
    metrics = {
        "active_subscriptions": active_subscriptions.count(),
        "successful_payments": successful_payments.count(),
        "total_spent": successful_payments.aggregate(total=Sum("amount"))["total"]
        or Decimal("0.000"),
        "course_progress": 0,
        "certificates": 0,
        "mentoring_sessions": 0,
    }
    if user.role == get_user_model().Role.ADMIN:
        ai_calls = list(AICallLog.objects.values("feature", "duration_ms", "success"))
        durations = sorted(call["duration_ms"] for call in ai_calls)
        p95_index = min(len(durations) - 1, round(len(durations) * 0.95) - 1) if durations else 0
        by_feature = {}
        for call in ai_calls:
            feature = by_feature.setdefault(call["feature"], {"total": 0, "failures": 0})
            feature["total"] += 1
            feature["failures"] += int(not call["success"])
        metrics.update(
            {
                "ai_calls": len(ai_calls),
                "ai_average_latency_ms": round(sum(durations) / len(durations), 2)
                if durations
                else 0,
                "ai_p95_latency_ms": durations[p95_index] if durations else 0,
                "ai_failure_rate": round(
                    sum(not call["success"] for call in ai_calls) / len(ai_calls) * 100, 2
                )
                if ai_calls
                else 0,
                "ai_by_feature": {
                    feature: round(values["failures"] / values["total"] * 100, 2)
                    for feature, values in by_feature.items()
                },
            }
        )
        metrics.update(
            {
                "users": get_user_model().objects.count(),
                "platform_revenue": Payment.objects.filter(
                    status=Payment.Status.SUCCEEDED
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0.000"),
                "platform_subscriptions": Subscription.objects.filter(
                    status=Subscription.Status.ACTIVE, ends_at__gt=now
                ).count(),
            }
        )
    return metrics
