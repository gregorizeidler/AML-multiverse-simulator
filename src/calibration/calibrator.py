from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.isotonic import IsotonicRegression


@dataclass
class CalibrationResult:
    method: str
    ece: float                      # Expected Calibration Error
    mce: float                      # Maximum Calibration Error
    reliability_diagram: list[dict] # fraction_positive vs mean_predicted_value
    brier_score: float
    is_calibrated: bool

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "ece": self.ece,
            "mce": self.mce,
            "brier_score": self.brier_score,
            "is_calibrated": self.is_calibrated,
            "reliability_diagram": self.reliability_diagram,
        }


class ModelCalibrator:
    """
    Applies Isotonic Regression calibration to a trained classifier and
    evaluates calibration quality via ECE, MCE, and reliability diagrams.

    Uncalibrated tree models (incl. XGBoost) are often overconfident —
    calibration maps raw scores to proper probabilities.
    """

    def __init__(self, n_bins: int = 10) -> None:
        self.n_bins = n_bins
        self._iso: IsotonicRegression | None = None

    def fit(self, y_scores: np.ndarray, y_true: np.ndarray) -> "ModelCalibrator":
        self._iso = IsotonicRegression(out_of_bounds="clip")
        self._iso.fit(y_scores, y_true)
        return self

    def transform(self, y_scores: np.ndarray) -> np.ndarray:
        if self._iso is None:
            return y_scores
        return np.clip(self._iso.predict(y_scores), 0, 1)

    def evaluate(
        self,
        y_scores: np.ndarray,
        y_true: np.ndarray,
        method: str = "isotonic",
    ) -> CalibrationResult:
        frac_pos, mean_pred = calibration_curve(
            y_true, y_scores, n_bins=self.n_bins, strategy="uniform"
        )

        ece = self._ece(y_scores, y_true)
        mce = float(np.max(np.abs(frac_pos - mean_pred)))
        brier = float(np.mean((y_scores - y_true) ** 2))
        is_calibrated = ece < 0.05

        diagram = [
            {"mean_predicted": round(float(mp), 4), "fraction_positive": round(float(fp), 4)}
            for mp, fp in zip(mean_pred.tolist(), frac_pos.tolist())
        ]

        return CalibrationResult(
            method=method,
            ece=round(ece, 6),
            mce=round(mce, 6),
            brier_score=round(brier, 6),
            is_calibrated=is_calibrated,
            reliability_diagram=diagram,
        )

    def evaluate_before_after(
        self,
        y_scores_raw: np.ndarray,
        y_true: np.ndarray,
    ) -> dict:
        self.fit(y_scores_raw, y_true)
        y_calibrated = self.transform(y_scores_raw)
        before = self.evaluate(y_scores_raw, y_true, method="raw")
        after = self.evaluate(y_calibrated, y_true, method="isotonic")
        return {
            "before": before.to_dict(),
            "after": after.to_dict(),
            "ece_improvement": round(before.ece - after.ece, 6),
            "brier_improvement": round(before.brier_score - after.brier_score, 6),
        }

    def _ece(self, y_scores: np.ndarray, y_true: np.ndarray) -> float:
        """Expected Calibration Error via adaptive binning."""
        n = len(y_scores)
        ece = 0.0
        bin_edges = np.linspace(0, 1, self.n_bins + 1)
        for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
            mask = (y_scores >= lo) & (y_scores < hi)
            if mask.sum() == 0:
                continue
            bin_conf = y_scores[mask].mean()
            bin_acc = y_true[mask].mean()
            ece += (mask.sum() / n) * abs(bin_conf - bin_acc)
        return float(ece)
