"""Evaluation metrics for offloading classification models."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

from .dataset import VALID_LABELS


@dataclass(frozen=True)
class ClassificationMetrics:
    """Classification metrics for binary offloading prediction."""

    accuracy: float
    precision_edge: float
    recall_edge: float
    f1_edge: float
    precision_cloud: float
    recall_cloud: float
    f1_cloud: float
    confusion_matrix: list[list[int]]
    prediction_distribution: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "precision_edge": self.precision_edge,
            "recall_edge": self.recall_edge,
            "f1_edge": self.f1_edge,
            "precision_cloud": self.precision_cloud,
            "recall_cloud": self.recall_cloud,
            "f1_cloud": self.f1_cloud,
            "confusion_matrix": self.confusion_matrix,
            "prediction_distribution": self.prediction_distribution,
        }


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> ClassificationMetrics:
    """Compute classification metrics for binary offloading prediction."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have same length")

    # Overall accuracy
    accuracy = float(np.mean(y_true == y_pred))

    # Per-class metrics (binary: Edge=0, Cloud=1 for sklearn)
    y_true_binary = (y_true == "Cloud").astype(int)
    y_pred_binary = (y_pred == "Cloud").astype(int)

    precision_cloud = float(precision_score(y_true_binary, y_pred_binary, zero_division=0))
    recall_cloud = float(recall_score(y_true_binary, y_pred_binary, zero_division=0))
    f1_cloud = float(f1_score(y_true_binary, y_pred_binary, zero_division=0))

    # For Edge, invert the binary labels
    precision_edge = float(precision_score(1 - y_true_binary, 1 - y_pred_binary, zero_division=0))
    recall_edge = float(recall_score(1 - y_true_binary, 1 - y_pred_binary, zero_division=0))
    f1_edge = float(f1_score(1 - y_true_binary, 1 - y_pred_binary, zero_division=0))

    # Confusion matrix (rows=true, cols=pred)
    cm = confusion_matrix(y_true, y_pred, labels=list(VALID_LABELS))
    confusion_matrix_list = cm.tolist()

    # Prediction distribution
    prediction_distribution = dict(Counter(y_pred))

    return ClassificationMetrics(
        accuracy=accuracy,
        precision_edge=precision_edge,
        recall_edge=recall_edge,
        f1_edge=f1_edge,
        precision_cloud=precision_cloud,
        recall_cloud=recall_cloud,
        f1_cloud=f1_cloud,
        confusion_matrix=confusion_matrix_list,
        prediction_distribution=prediction_distribution,
    )


def format_metrics_table(metrics: dict[str, ClassificationMetrics | dict[str, Any]]) -> str:
    """Format metrics comparison table as Markdown."""
    lines = [
        "| Modelo   | Accuracy | Precision Edge | Recall Edge | F1 Edge | Precision Cloud | Recall Cloud | F1 Cloud |",
        "| -------- | -------: | -------------: | ----------: | ------: | --------------: | -----------: | -------: |",
    ]

    for model_name, m in sorted(metrics.items()):
        # Handle both ClassificationMetrics objects and dicts
        if isinstance(m, dict):
            acc = m.get("accuracy", 0)
            prec_edge = m.get("precision_edge", 0)
            rec_edge = m.get("recall_edge", 0)
            f1_edge = m.get("f1_edge", 0)
            prec_cloud = m.get("precision_cloud", 0)
            rec_cloud = m.get("recall_cloud", 0)
            f1_cloud = m.get("f1_cloud", 0)
        else:
            acc = m.accuracy
            prec_edge = m.precision_edge
            rec_edge = m.recall_edge
            f1_edge = m.f1_edge
            prec_cloud = m.precision_cloud
            rec_cloud = m.recall_cloud
            f1_cloud = m.f1_cloud

        lines.append(
            f"| {model_name} | {acc:.4f} | {prec_edge:.4f} | "
            f"{rec_edge:.4f} | {f1_edge:.4f} | {prec_cloud:.4f} | "
            f"{rec_cloud:.4f} | {f1_cloud:.4f} |"
        )

    return "\n".join(lines)


def format_config_table(configs: dict[str, dict[str, Any]]) -> str:
    """Format model configuration table as Markdown."""
    lines = [
        "| Modelo | Seed | Preprocessing | Principais hiperparâmetros |",
        "| ------ | ---: | ------------- | -------------------------- |",
    ]

    for model_name, config in sorted(configs.items()):
        preprocessing = config.get("preprocessing", "N/A")
        hyperparams = config.get("hyperparameters", "N/A")

        # Format hyperparams as key=value pairs
        if isinstance(hyperparams, dict):
            hyperparam_str = ", ".join(f"{k}={v}" for k, v in hyperparams.items())
        else:
            hyperparam_str = str(hyperparams)

        seed = config.get("seed", "N/A")

        lines.append(f"| {model_name} | {seed} | {preprocessing} | {hyperparam_str} |")

    return "\n".join(lines)
