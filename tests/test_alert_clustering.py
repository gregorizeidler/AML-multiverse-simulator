"""Tests for alert clustering and case management."""

import numpy as np
import pandas as pd
import pytest

from src.alert_clustering.clusterer import AlertClusterer, Case


@pytest.fixture
def sample_alerts():
    rng = np.random.default_rng(42)
    n = 100
    return pd.DataFrame({
        "tx_id":           [f"TX-{i}" for i in range(n)],
        "from_account":    [f"ACC-{rng.integers(0, 20)}" for _ in range(n)],
        "to_account":      [f"ACC-{rng.integers(20, 40)}" for _ in range(n)],
        "amount":          rng.lognormal(8, 1.5, n),
        "alert_score":     rng.uniform(0.5, 8.0, n),
        "amount_zscore":   rng.normal(0, 2, n),
        "tx_count_1h":     rng.integers(1, 50, n),
        "behavioral_anomaly_score": rng.uniform(0, 1, n),
        "betweenness_centrality":   rng.uniform(0, 0.5, n),
        "pass_through_ratio":       rng.uniform(0, 1, n),
        "illicit_typology":  rng.choice(["smurfing", "layering", None], n),
    })


def test_clusterer_returns_cases(sample_alerts):
    clusterer = AlertClusterer(universe_id="test_universe")
    cases = clusterer.cluster(sample_alerts)
    assert isinstance(cases, list)
    assert len(cases) > 0


def test_case_structure(sample_alerts):
    clusterer = AlertClusterer(universe_id="test_universe")
    cases = clusterer.cluster(sample_alerts)
    for case in cases:
        assert isinstance(case, Case)
        assert case.case_id.startswith("CASE-")
        assert case.n_alerts >= 1
        assert case.priority in ("critical", "high", "medium", "low", "noise")
        assert case.status in ("open", "noise")


def test_case_to_dict(sample_alerts):
    clusterer = AlertClusterer(universe_id="test_universe")
    cases = clusterer.cluster(sample_alerts)
    d = cases[0].to_dict()
    assert "case_id" in d
    assert "n_alerts" in d
    assert "priority" in d
    assert "total_amount" in d


def test_empty_alerts():
    clusterer = AlertClusterer()
    cases = clusterer.cluster(pd.DataFrame())
    assert cases == []


def test_minimal_alerts():
    df = pd.DataFrame({
        "tx_id": ["TX-1", "TX-2"],
        "from_account": ["ACC-1", "ACC-2"],
        "amount": [5000, 8000],
    })
    clusterer = AlertClusterer(universe_id="minimal")
    cases = clusterer.cluster(df)
    assert len(cases) >= 1
