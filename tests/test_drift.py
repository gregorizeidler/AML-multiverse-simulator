"""Tests for drift detection (KS test + PSI)."""

import numpy as np
import pandas as pd
import pytest

from src.drift.detector import DriftDetector, DriftReport, FeatureDrift


@pytest.fixture
def stable_data():
    rng = np.random.default_rng(42)
    n = 500
    base = {
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h"),
        "amount":    rng.lognormal(7, 1, n),
        "amount_zscore":  rng.normal(0, 1, n),
        "tx_count_1h": rng.integers(1, 20, n).astype(float),
        "behavioral_anomaly_score": rng.uniform(0, 1, n),
    }
    df = pd.DataFrame(base)
    return df.iloc[:n//2], df.iloc[n//2:]


@pytest.fixture
def drifted_data():
    rng = np.random.default_rng(99)
    n = 500
    ref = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n//2, freq="h"),
        "amount":    rng.lognormal(7, 1, n//2),
        "amount_zscore": rng.normal(0, 1, n//2),
        "tx_count_1h": rng.integers(1, 20, n//2).astype(float),
    })
    cur = pd.DataFrame({
        "timestamp": pd.date_range("2024-06-01", periods=n//2, freq="h"),
        "amount":    rng.lognormal(10, 2, n//2),  # heavy drift
        "amount_zscore": rng.normal(5, 3, n//2),  # shifted mean
        "tx_count_1h": rng.integers(50, 200, n//2).astype(float),
    })
    return ref, cur


def test_stable_data_no_drift(stable_data):
    ref, cur = stable_data
    detector = DriftDetector()
    report = detector.detect(ref, cur)
    assert isinstance(report, DriftReport)
    assert report.severity in ("none", "low")


def test_drifted_data_detected(drifted_data):
    ref, cur = drifted_data
    detector = DriftDetector()
    report = detector.detect(ref, cur)
    assert report.n_features_drifted > 0
    assert report.severity in ("medium", "high")


def test_report_structure(stable_data):
    ref, cur = stable_data
    report = DriftDetector().detect(ref, cur)
    d = report.to_dict()
    assert "overall_drift_score" in d
    assert "n_features_monitored" in d
    assert "features" in d
    for f in d["features"]:
        assert "ks_statistic" in f
        assert "p_value" in f
        assert "psi" in f


def test_temporal_drift(stable_data):
    ref, cur = stable_data
    full = pd.concat([ref, cur]).reset_index(drop=True)
    reports = DriftDetector().detect_temporal(full, n_windows=4)
    assert len(reports) == 3  # n_windows - 1


def test_psi_calculation():
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 1000)
    cur = rng.normal(5, 1, 1000)  # large shift
    psi = DriftDetector._psi(ref, cur)
    assert psi > 0.25  # should flag major shift
