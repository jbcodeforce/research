"""Train, persist, and load the sklearn classifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from reefer_pm_kafka.config import FAILURE_CLASSES, FEATURE_COLUMNS
from reefer_pm_kafka.features import FeatureRow


def build_pipeline() -> Pipeline:
    """Standardize features then classify with balanced random forest."""
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=100,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def train_model(
    rows: list[FeatureRow],
) -> tuple[Pipeline, dict[str, Any]]:
    """Fit pipeline on labeled feature rows."""
    labeled = [r for r in rows if r.label in FAILURE_CLASSES]
    if len(labeled) < 10:
        raise ValueError(f"need at least 10 labeled windows, got {len(labeled)}")

    x = np.array([[r.features[c] for c in FEATURE_COLUMNS] for r in labeled])
    y = np.array([r.label for r in labeled])
    pipe = build_pipeline()
    pipe.fit(x, y)
    train_acc = float(accuracy_score(y, pipe.predict(x)))
    meta = {"train_windows": len(labeled), "train_accuracy": train_acc}
    return pipe, meta


def save_model(pipe: Pipeline, path: Path, *, version: str, extra: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {"version": version, "pipeline": pipe, "feature_columns": FEATURE_COLUMNS}
    if extra:
        bundle["meta"] = extra
    joblib.dump(bundle, path)


def load_model(path: Path) -> tuple[Pipeline, str, list[str]]:
    bundle = joblib.load(path)
    return bundle["pipeline"], bundle["version"], bundle["feature_columns"]


def predict_row(pipe: Pipeline, row: FeatureRow) -> tuple[str, float]:
    x = np.array([[row.features[c] for c in FEATURE_COLUMNS]])
    proba = pipe.predict_proba(x)[0]
    classes = list(pipe.named_steps["clf"].classes_)
    idx = int(np.argmax(proba))
    return classes[idx], float(proba[idx])


def evaluate_predictions(
    y_true: list[str],
    y_pred: list[str],
) -> dict[str, Any]:
    """Compute metrics and confusion matrix for test split."""
    labels = list(FAILURE_CLASSES)
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "per_class": report,
        "confusion_matrix": {"labels": labels, "counts": cm},
    }
