"""Tests for GNN Universe (spectral tier — no PyTorch required)."""
import numpy as np
import pandas as pd
import pytest

from src.gnn_universe.model import GNNScorer


@pytest.fixture
def sample_data():
    rng = np.random.default_rng(0)
    n = 300
    accounts = pd.DataFrame({
        "account_id": [f"ACC-{i}" for i in range(50)],
        "country": rng.choice(["US", "MX", "DE"], 50),
    })
    txns = pd.DataFrame({
        "tx_id": [f"T{i}" for i in range(n)],
        "from_account": [f"ACC-{rng.integers(0, 50)}" for _ in range(n)],
        "to_account":   [f"ACC-{rng.integers(0, 50)}" for _ in range(n)],
        "amount":       rng.lognormal(7, 1.5, n),
        "timestamp":    pd.date_range("2023-01-01", periods=n, freq="2h"),
        "is_illicit":   rng.binomial(1, 0.1, n).astype(bool),
        "amount_zscore":        rng.normal(0, 1, n),
        "tx_count_24h":         rng.integers(1, 20, n).astype(float),
        "behavioral_anomaly_score": rng.uniform(0, 1, n),
        "betweenness_centrality": rng.uniform(0, 0.5, n),
        "pass_through_ratio":    rng.uniform(0, 1, n),
    })
    return txns, accounts


def test_gnn_scorer_produces_scores(sample_data):
    txns, accounts = sample_data
    scorer = GNNScorer(seed=42)
    result = scorer.fit_score(txns, accounts)
    assert "gnn_score" in result.columns


def test_gnn_score_range(sample_data):
    txns, accounts = sample_data
    result = GNNScorer(seed=42).fit_score(txns, accounts)
    assert result["gnn_score"].between(0, 1).all()


def test_gnn_score_not_constant(sample_data):
    txns, accounts = sample_data
    result = GNNScorer(seed=42).fit_score(txns, accounts)
    assert result["gnn_score"].std() > 0.001


def test_gnn_tier_spectral(sample_data):
    txns, accounts = sample_data
    scorer = GNNScorer(seed=42)
    scorer.fit_score(txns, accounts)
    assert scorer.tier in ("spectral", "graphsage")


def test_gnn_preserves_row_count(sample_data):
    txns, accounts = sample_data
    result = GNNScorer(seed=42).fit_score(txns, accounts)
    assert len(result) == len(txns)
