"""Tests for model calibration (isotonic regression + ECE)."""

import numpy as np
import pytest

from src.calibration.calibrator import ModelCalibrator, CalibrationResult


@pytest.fixture
def uncalibrated_scores():
    rng = np.random.default_rng(42)
    y_true = rng.binomial(1, 0.1, 1000)
    # Overconfident scores: compressed towards extremes
    y_scores = np.where(y_true == 1,
                        rng.uniform(0.8, 1.0, 1000),
                        rng.uniform(0.0, 0.4, 1000))
    return y_scores, y_true


def test_calibrator_fit_transform(uncalibrated_scores):
    y_scores, y_true = uncalibrated_scores
    cal = ModelCalibrator()
    cal.fit(y_scores, y_true)
    calibrated = cal.transform(y_scores)
    assert calibrated.shape == y_scores.shape
    assert calibrated.min() >= 0.0
    assert calibrated.max() <= 1.0


def test_calibration_result_structure(uncalibrated_scores):
    y_scores, y_true = uncalibrated_scores
    cal = ModelCalibrator()
    cal.fit(y_scores, y_true)
    result = cal.evaluate(y_scores, y_true)
    assert isinstance(result, CalibrationResult)
    assert result.ece >= 0.0
    assert result.mce >= 0.0
    assert result.brier_score > 0.0
    assert len(result.reliability_diagram) > 0


def test_before_after_calibration(uncalibrated_scores):
    y_scores, y_true = uncalibrated_scores
    cal = ModelCalibrator()
    result = cal.evaluate_before_after(y_scores, y_true)
    assert "before" in result
    assert "after" in result
    assert "ece_improvement" in result


def test_ece_perfect_calibration():
    """A perfectly calibrated model has ECE ≈ 0."""
    n = 1000
    y_scores = np.linspace(0, 1, n)
    rng = np.random.default_rng(0)
    y_true = rng.binomial(1, y_scores)
    cal = ModelCalibrator()
    ece = cal._ece(y_scores, y_true)
    assert ece < 0.15  # should be low for calibrated model
