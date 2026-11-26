import numpy as np
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_recall_curve, precision_score, recall_score, roc_auc_score,
)


def select_f1_threshold(y: np.ndarray, score: np.ndarray) -> float:
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    if len(y) == 0 or len(y) != len(score) or not np.isfinite(score).all():
        raise ValueError("Threshold selection requires aligned, non-empty, finite labels and scores")
    precision, recall, thresholds = precision_recall_curve(y, score)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(precision), where=(precision + recall) > 0)
    best = np.flatnonzero(f1[:-1] == np.max(f1[:-1]))
    return float(np.max(thresholds[best])) if len(best) else 0.5


def binary_metrics(y: np.ndarray, score: np.ndarray, threshold: float) -> dict:
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    if len(y) == 0 or len(y) != len(score) or not np.isfinite(score).all():
        raise ValueError("Evaluation requires aligned, non-empty, finite labels and scores")
    prediction = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    return {
        "pr_auc": float(average_precision_score(y, score)) if np.any(y == 1) else float("nan"),
        "roc_auc": float(roc_auc_score(y, score)) if 0 < np.sum(y) < len(y) else float("nan"),
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "false_alarm_rate": float(fp / (fp + tn)) if fp + tn else float("nan"),
        "accuracy": float(accuracy_score(y, prediction)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "positive_support": int(np.sum(y)), "negative_support": int(len(y) - np.sum(y)),
        "threshold": float(threshold),
    }
