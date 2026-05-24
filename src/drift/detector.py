from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

MONITORED_FEATURES = [
    "amount", "amount_zscore", "tx_count_1h", "tx_count_24h",
    "amount_24h", "unique_counterparties_7d", "behavioral_anomaly_score",
    "betweenness_centrality", "pass_through_ratio", "fan_out_ratio",
]


@dataclass
class FeatureDrift:
    feature: str
    ks_statistic: float
    p_value: float
    psi: float
    is_drifted: bool
    severity: str          # "none" | "low" | "medium" | "high"
    reference_mean: float
    current_mean: float
    mean_shift_pct: float  # % change in mean

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "ks_statistic": self.ks_statistic,
            "p_value": self.p_value,
            "psi": self.psi,
            "is_drifted": self.is_drifted,
            "severity": self.severity,
            "reference_mean": self.reference_mean,
            "current_mean": self.current_mean,
            "mean_shift_pct": self.mean_shift_pct,
        }


@dataclass
class DriftReport:
    reference_period: str
    current_period: str
    n_features_monitored: int
    n_features_drifted: int
    overall_drift_score: float       # 0 = no drift, 1 = severe drift
    severity: str
    features: list[FeatureDrift]
    alert_rate_drift: float | None   # change in % of transactions alerted
    illicit_rate_drift: float | None

    def to_dict(self) -> dict:
        return {
            "reference_period": self.reference_period,
            "current_period": self.current_period,
            "n_features_monitored": self.n_features_monitored,
            "n_features_drifted": self.n_features_drifted,
            "overall_drift_score": self.overall_drift_score,
            "severity": self.severity,
            "alert_rate_drift": self.alert_rate_drift,
            "illicit_rate_drift": self.illicit_rate_drift,
            "features": [f.to_dict() for f in self.features],
        }


class DriftDetector:
    """
    Detects distribution shift between a reference window (training period)
    and a current window (recent production data) using:

      1. Kolmogorov-Smirnov test (p-value < 0.05 → drift)
      2. Population Stability Index (PSI > 0.25 → major shift)
    """

    def __init__(
        self,
        ks_alpha: float = 0.05,
        psi_threshold_low: float = 0.10,
        psi_threshold_high: float = 0.25,
    ) -> None:
        self.ks_alpha = ks_alpha
        self.psi_threshold_low = psi_threshold_low
        self.psi_threshold_high = psi_threshold_high

    def detect(
        self,
        reference: pd.DataFrame,
        current: pd.DataFrame,
        reference_label: str = "reference",
        current_label: str = "current",
    ) -> DriftReport:
        feature_drifts = []
        available = [f for f in MONITORED_FEATURES if f in reference.columns and f in current.columns]

        for feat in available:
            ref_vals = reference[feat].dropna().values
            cur_vals = current[feat].dropna().values

            if len(ref_vals) < 10 or len(cur_vals) < 10:
                continue

            fd = self._analyze_feature(feat, ref_vals, cur_vals)
            feature_drifts.append(fd)

        n_drifted = sum(1 for f in feature_drifts if f.is_drifted)
        overall_score = round(
            np.mean([f.ks_statistic for f in feature_drifts]) if feature_drifts else 0.0, 4
        )

        severity = (
            "high"   if overall_score > 0.3
            else "medium" if overall_score > 0.15
            else "low"    if overall_score > 0.05
            else "none"
        )

        # Alert rate drift
        alert_rate_drift = None
        if "is_alerted" in reference.columns and "is_alerted" in current.columns:
            ref_rate = reference["is_alerted"].mean()
            cur_rate = current["is_alerted"].mean()
            alert_rate_drift = round(cur_rate - ref_rate, 4)

        illicit_rate_drift = None
        if "is_illicit" in reference.columns and "is_illicit" in current.columns:
            ref_rate = reference["is_illicit"].mean()
            cur_rate = current["is_illicit"].mean()
            illicit_rate_drift = round(cur_rate - ref_rate, 4)

        return DriftReport(
            reference_period=reference_label,
            current_period=current_label,
            n_features_monitored=len(feature_drifts),
            n_features_drifted=n_drifted,
            overall_drift_score=overall_score,
            severity=severity,
            features=sorted(feature_drifts, key=lambda f: f.ks_statistic, reverse=True),
            alert_rate_drift=alert_rate_drift,
            illicit_rate_drift=illicit_rate_drift,
        )

    def detect_temporal(
        self,
        df: pd.DataFrame,
        n_windows: int = 4,
    ) -> list[DriftReport]:
        """Split df into windows and detect drift between each consecutive pair."""
        df = df.sort_values("timestamp").reset_index(drop=True)
        window_size = len(df) // n_windows
        reports = []

        for i in range(n_windows - 1):
            ref = df.iloc[i * window_size : (i + 1) * window_size]
            cur = df.iloc[(i + 1) * window_size : (i + 2) * window_size]
            report = self.detect(
                ref, cur,
                reference_label=f"W{i+1}",
                current_label=f"W{i+2}",
            )
            reports.append(report)

        return reports

    def _analyze_feature(
        self, feat: str, ref: np.ndarray, cur: np.ndarray
    ) -> FeatureDrift:
        ks_stat, p_value = ks_2samp(ref, cur)
        psi = self._psi(ref, cur)
        is_drifted = (p_value < self.ks_alpha) or (psi > self.psi_threshold_low)
        severity = (
            "high"   if psi > self.psi_threshold_high or ks_stat > 0.3
            else "medium" if psi > self.psi_threshold_low or ks_stat > 0.15
            else "low"    if is_drifted
            else "none"
        )
        ref_mean = float(np.mean(ref))
        cur_mean = float(np.mean(cur))
        shift_pct = round((cur_mean - ref_mean) / max(abs(ref_mean), 1e-9) * 100, 2)

        return FeatureDrift(
            feature=feat,
            ks_statistic=round(float(ks_stat), 6),
            p_value=round(float(p_value), 6),
            psi=round(psi, 6),
            is_drifted=bool(is_drifted),
            severity=severity,
            reference_mean=round(ref_mean, 4),
            current_mean=round(cur_mean, 4),
            mean_shift_pct=shift_pct,
        )

    @staticmethod
    def _psi(ref: np.ndarray, cur: np.ndarray, n_bins: int = 10) -> float:
        """Population Stability Index."""
        bins = np.percentile(ref, np.linspace(0, 100, n_bins + 1))
        bins = np.unique(bins)
        if len(bins) < 2:
            return 0.0

        ref_counts, _ = np.histogram(ref, bins=bins)
        cur_counts, _ = np.histogram(cur, bins=bins)

        ref_pct = ref_counts / max(ref_counts.sum(), 1)
        cur_pct = cur_counts / max(cur_counts.sum(), 1)

        ref_pct = np.where(ref_pct == 0, 1e-4, ref_pct)
        cur_pct = np.where(cur_pct == 0, 1e-4, cur_pct)

        psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
        return float(np.clip(psi, 0, 10))
