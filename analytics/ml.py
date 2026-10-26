"""Synthetic dropout-risk dataset generation and model training utilities."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES = (
    "days_since_last_activity",
    "progress_percent",
    "average_quiz_score",
    "mentoring_sessions",
    "forum_messages",
    "account_age_days",
)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def generate_dataset(samples: int = 200, seed: int = 42) -> list[dict[str, Any]]:
    """Generate a deterministic, synthetic learner dataset.

    Labels are produced from realistic risk signals plus a small amount of noise.
    This dataset must never be presented as production learner data.
    """
    if samples < 20:
        raise ValueError("samples must be at least 20")

    rng = random.Random(seed)
    rows = []
    for _ in range(samples):
        account_age = rng.randint(14, 730)
        progress = _clamp(rng.gauss(58, 25), 0, 100)
        quiz_score = _clamp(rng.gauss(64 + progress * 0.12, 18), 0, 100)
        mentoring = rng.randint(0, 8)
        forum_messages = min(max(int(rng.gauss(8, 10)), 0), 60)
        # Learners with low progress and little recent activity are higher risk.
        activity_baseline = 28 - progress * 0.16 - mentoring * 1.5 - forum_messages * 0.12
        days_since_activity = int(_clamp(rng.gauss(activity_baseline, 8), 0, 120))
        signal = (
            0.045 * days_since_activity
            - 0.035 * progress
            - 0.018 * quiz_score
            - 0.12 * mentoring
            - 0.025 * forum_messages
            + 0.001 * max(account_age - 180, 0)
            + rng.gauss(0, 0.7)
        )
        dropout = int(signal > -1.5)
        rows.append(
            {
                "days_since_last_activity": days_since_activity,
                "progress_percent": round(progress, 2),
                "average_quiz_score": round(quiz_score, 2),
                "mentoring_sessions": mentoring,
                "forum_messages": forum_messages,
                "account_age_days": account_age,
                "dropout": dropout,
            }
        )
    return rows


def _matrix(rows: list[dict[str, Any]]) -> tuple[list[list[float]], list[int]]:
    features = [[float(row[name]) for name in FEATURE_NAMES] for row in rows]
    labels = [int(row["dropout"]) for row in rows]
    return features, labels


def train_and_evaluate(
    rows: list[dict[str, Any]], output_path: str | Path,
    metrics_path: str | Path | None = None, seed: int = 42,
) -> dict[str, Any]:
    """Compare two classifiers, save the best one, and return evaluation metrics."""
    features, labels = _matrix(rows)
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=seed, stratify=labels
    )
    candidates = {
        "logistic_regression": Pipeline(
            [("scaler", StandardScaler()), ("classifier", LogisticRegression(max_iter=1000))]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=150, random_state=seed, class_weight="balanced"
        ),
    }
    evaluations = {}
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        probabilities = model.predict_proba(x_test)[:, 1]
        try:
            roc_auc = round(roc_auc_score(y_test, probabilities), 4)
        except ValueError:
            roc_auc = 0.5
        evaluations[name] = {
            "accuracy": round(accuracy_score(y_test, predictions), 4),
            "precision": round(precision_score(y_test, predictions, zero_division=0), 4),
            "recall": round(recall_score(y_test, predictions, zero_division=0), 4),
            "f1": round(f1_score(y_test, predictions, zero_division=0), 4),
            "confusion_matrix": confusion_matrix(y_test, predictions, labels=[0, 1]).tolist(),
            "roc_auc": roc_auc,
        }

    best_name = max(
        evaluations,
        key=lambda name: (evaluations[name]["f1"], evaluations[name]["roc_auc"]),
    )
    best_model = candidates[best_name]
    best_model.fit(features, labels)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": best_model, "features": FEATURE_NAMES}, output)
    result = {
        "dataset_size": len(rows),
        "test_size": len(y_test),
        "best_model": best_name,
        "features": list(FEATURE_NAMES),
        "models": evaluations,
    }
    if metrics_path:
        metrics_file = Path(metrics_path)
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        metrics_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def predict_dropout_risk(model_path: str | Path, features: dict[str, float]) -> dict[str, Any]:
    """Return a probability and a user-facing low/medium/high risk label."""
    bundle = joblib.load(model_path)
    values = [[float(features[name]) for name in bundle["features"]]]
    probability = float(bundle["model"].predict_proba(values)[0, 1])
    if probability < 0.34:
        level = "low"
    elif probability < 0.67:
        level = "medium"
    else:
        level = "high"
    return {"probability": round(probability, 4), "level": level}
