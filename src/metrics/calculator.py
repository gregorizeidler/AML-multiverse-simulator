from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ..rule_engine.loader import UniverseConfig


class MetricsCalculator:
    """
    Computes all detection quality and business cost metrics for a universe.
    """

    def __init__(self, config: UniverseConfig) -> None:
        self.config = config

    def compute(self, evaluated: pd.DataFrame) -> dict[str, Any]:
        y_true = evaluated["is_illicit"].astype(int).values
        y_pred = evaluated["is_alerted"].astype(int).values
        y_score = evaluated["alert_score"].values

        if y_true.sum() == 0:
            return self._empty_metrics(evaluated)

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        fpr = fp / max(fp + tn, 1)

        # Normalize scores for AUC
        score_min, score_max = y_score.min(), y_score.max()
        if score_max > score_min:
            y_score_norm = (y_score - score_min) / (score_max - score_min)
        else:
            y_score_norm = y_score

        try:
            auc_roc = roc_auc_score(y_true, y_score_norm)
        except Exception:
            auc_roc = 0.5

        try:
            auc_pr = average_precision_score(y_true, y_score_norm)
        except Exception:
            auc_pr = 0.0

        # Business cost model
        cost = self._cost_metrics(tp, fp, fn)

        return {
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "false_positive_rate": round(float(fpr), 4),
            "auc_roc": round(float(auc_roc), 4),
            "auc_pr": round(float(auc_pr), 4),
            "n_alerts": int(y_pred.sum()),
            "n_illicit": int(y_true.sum()),
            "n_transactions": len(evaluated),
            **cost,
        }

    def _cost_metrics(self, tp: int, fp: int, fn: int) -> dict[str, float]:
        inv_cost = (tp + fp) * self.config.cost_model.investigation_cost_per_alert
        missed_cost = fn * self.config.cost_model.missed_laundering_cost_per_txn
        total_cost = inv_cost + missed_cost
        return {
            "investigation_cost": round(inv_cost, 2),
            "missed_laundering_cost": round(missed_cost, 2),
            "total_cost": round(total_cost, 2),
        }

    def _empty_metrics(self, evaluated: pd.DataFrame) -> dict[str, Any]:
        return {
            "true_positives": 0,
            "false_positives": 0,
            "true_negatives": len(evaluated),
            "false_negatives": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "false_positive_rate": 0.0,
            "auc_roc": 0.5,
            "auc_pr": 0.0,
            "n_alerts": 0,
            "n_illicit": 0,
            "n_transactions": len(evaluated),
            "investigation_cost": 0.0,
            "missed_laundering_cost": 0.0,
            "total_cost": 0.0,
        }
