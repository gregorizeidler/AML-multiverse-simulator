import pandas as pd
import pytest
from pathlib import Path

from src.metrics.calculator import MetricsCalculator
from src.ranking.ranker import UniverseRanker
from src.rule_engine.loader import load_universe_config


CONFIG_DIR = Path("config/universes")


@pytest.fixture
def config():
    path = CONFIG_DIR / "universe_balanced.yaml"
    if not path.exists():
        pytest.skip("Config file not found")
    return load_universe_config(path)


def _make_evaluated(tp=10, fp=5, fn=3, tn=100):
    """Build a minimal evaluated DataFrame."""
    rows = (
        [{"is_illicit": True, "is_alerted": True, "alert_score": 5.0}] * tp
        + [{"is_illicit": False, "is_alerted": True, "alert_score": 3.0}] * fp
        + [{"is_illicit": True, "is_alerted": False, "alert_score": 0.5}] * fn
        + [{"is_illicit": False, "is_alerted": False, "alert_score": 0.1}] * tn
    )
    return pd.DataFrame(rows)


def test_metrics_calculator_basic(config):
    df = _make_evaluated(tp=10, fp=5, fn=3, tn=100)
    calc = MetricsCalculator(config)
    m = calc.compute(df)
    assert m["true_positives"] == 10
    assert m["false_positives"] == 5
    assert m["false_negatives"] == 3
    assert m["true_negatives"] == 100
    assert 0 <= m["f1"] <= 1
    assert 0 <= m["recall"] <= 1
    assert 0 <= m["precision"] <= 1


def test_metrics_cost_calculation(config):
    df = _make_evaluated(tp=10, fp=5, fn=3, tn=100)
    calc = MetricsCalculator(config)
    m = calc.compute(df)
    expected_inv_cost = (10 + 5) * 150
    expected_missed_cost = 3 * 50_000
    assert m["investigation_cost"] == pytest.approx(expected_inv_cost)
    assert m["missed_laundering_cost"] == pytest.approx(expected_missed_cost)
    assert m["total_cost"] == pytest.approx(expected_inv_cost + expected_missed_cost)


def test_metrics_empty_illicit(config):
    df = pd.DataFrame([{"is_illicit": False, "is_alerted": False, "alert_score": 0.0}] * 50)
    calc = MetricsCalculator(config)
    m = calc.compute(df)
    assert m["recall"] == 0.0
    assert m["f1"] == 0.0


class FakeUniverse:
    def __init__(self, universe_id, name, metrics, rank=None):
        self.universe_id = universe_id
        self.name = name
        self.metrics = metrics
        self.rank = rank


def test_ranker_assigns_ranks():
    universes = [
        FakeUniverse("u1", "A", {"f1": 0.8, "recall": 0.85, "false_positive_rate": 0.05, "total_cost": 100_000}),
        FakeUniverse("u2", "B", {"f1": 0.5, "recall": 0.6, "false_positive_rate": 0.20, "total_cost": 500_000}),
        FakeUniverse("u3", "C", {"f1": 0.65, "recall": 0.7, "false_positive_rate": 0.10, "total_cost": 300_000}),
    ]
    ranker = UniverseRanker()
    ranked = ranker.rank(universes)
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[2].rank == 3
    assert ranked[0].universe_id == "u1"


def test_ranker_best_is_first():
    universes = [
        FakeUniverse("u_bad", "Bad", {"f1": 0.2, "recall": 0.1, "false_positive_rate": 0.9, "total_cost": 9_000_000}),
        FakeUniverse("u_good", "Good", {"f1": 0.9, "recall": 0.92, "false_positive_rate": 0.02, "total_cost": 50_000}),
    ]
    ranked = UniverseRanker().rank(universes)
    assert ranked[0].universe_id == "u_good"
