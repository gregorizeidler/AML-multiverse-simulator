"""Tests for Bayesian threshold optimizer."""
import numpy as np
import pandas as pd
import pytest

from src.optimization.threshold_optimizer import ThresholdOptimizer, OptimizationResult
from src.rule_engine.loader import load_universe_config
from pathlib import Path


CONFIG_DIR = Path("./config/universes")


@pytest.fixture
def sample_features():
    rng = np.random.default_rng(42)
    n = 500
    return pd.DataFrame({
        "tx_id": [f"T{i}" for i in range(n)],
        "from_account": [f"ACC-{rng.integers(0, 50)}" for _ in range(n)],
        "amount": rng.lognormal(7, 1.5, n),
        "amount_zscore": rng.normal(0, 2, n),
        "tx_count_1h": rng.integers(1, 30, n).astype(float),
        "tx_count_24h": rng.integers(1, 100, n).astype(float),
        "amount_24h": rng.lognormal(9, 1.5, n),
        "is_cross_border": rng.binomial(1, 0.15, n).astype(float),
        "behavioral_anomaly_score": rng.uniform(0, 1, n),
        "betweenness_centrality": rng.uniform(0, 0.5, n),
        "pass_through_ratio": rng.uniform(0, 1, n),
        "is_illicit": rng.binomial(1, 0.08, n).astype(bool),
        "alert_score": rng.uniform(0, 10, n),
        "is_alerted": rng.binomial(1, 0.2, n).astype(bool),
    })


@pytest.fixture
def config():
    return load_universe_config(CONFIG_DIR / "universe_balanced.yaml")


def test_optimizer_returns_result(sample_features, config):
    opt = ThresholdOptimizer(n_trials=5, seed=42)
    result = opt.optimize(config, sample_features, None, baseline_score=0.0)
    assert isinstance(result, OptimizationResult)


def test_result_has_thresholds(sample_features, config):
    opt = ThresholdOptimizer(n_trials=5, seed=42)
    result = opt.optimize(config, sample_features, None)
    assert len(result.best_thresholds) > 0


def test_result_to_dict(sample_features, config):
    opt = ThresholdOptimizer(n_trials=5, seed=42)
    result = opt.optimize(config, sample_features, None)
    d = result.to_dict()
    assert "best_score" in d
    assert "best_thresholds" in d
    assert "n_trials" in d
    assert "improvement_over_baseline" in d


def test_n_trials_respected(sample_features, config):
    opt = ThresholdOptimizer(n_trials=10, seed=42)
    result = opt.optimize(config, sample_features, None)
    assert result.n_trials >= 5  # at least some trials ran


def test_evaluate_config_score_range(sample_features, config):
    opt = ThresholdOptimizer()
    score = opt._evaluate_config(config.raw, sample_features)
    assert -2.0 <= score <= 2.0
