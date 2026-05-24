"""Tests for time-series feature extraction."""

import numpy as np
import pandas as pd
import pytest

from src.features.timeseries import TimeSeriesFeatures


@pytest.fixture
def sample_txns():
    rng = np.random.default_rng(0)
    n = 200
    return pd.DataFrame({
        "tx_id":        [f"TX-{i}" for i in range(n)],
        "from_account": [f"ACC-{rng.integers(0, 10)}" for _ in range(n)],
        "to_account":   [f"ACC-{rng.integers(10, 20)}" for _ in range(n)],
        "amount":       rng.lognormal(7, 1.5, n),
        "timestamp":    pd.date_range("2024-01-01", periods=n, freq="3h"),
    })


def test_calendar_features(sample_txns):
    ts = TimeSeriesFeatures()
    result = ts.transform(sample_txns)
    for col in ["hour_of_day", "day_of_week", "is_weekend", "is_night", "month", "quarter"]:
        assert col in result.columns


def test_cyclic_encoding(sample_txns):
    result = TimeSeriesFeatures().transform(sample_txns)
    for col in ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos"]:
        assert col in result.columns
        assert result[col].between(-1, 1).all()


def test_account_age(sample_txns):
    result = TimeSeriesFeatures().transform(sample_txns)
    assert "account_age_days" in result.columns
    assert result["account_age_days"].min() >= 0


def test_hour_anomaly(sample_txns):
    result = TimeSeriesFeatures().transform(sample_txns)
    assert "hour_anomaly" in result.columns
    assert result["hour_anomaly"].ge(0).all()


def test_is_night_range(sample_txns):
    result = TimeSeriesFeatures().transform(sample_txns)
    assert result["is_night"].isin([0, 1]).all()


def test_is_weekend_range(sample_txns):
    result = TimeSeriesFeatures().transform(sample_txns)
    assert result["is_weekend"].isin([0, 1]).all()
