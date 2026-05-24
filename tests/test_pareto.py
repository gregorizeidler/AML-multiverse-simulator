"""Tests for Pareto frontier ranking."""
import pytest
from unittest.mock import MagicMock

from src.ranking.ranker import UniverseRanker


def _make_universe(uid, f1, recall, fpr, cost):
    u = MagicMock()
    u.universe_id = uid
    u.name = uid
    u.rank = 99
    u.metrics = {
        "f1": f1,
        "recall": recall,
        "false_positive_rate": fpr,
        "total_cost": cost,
    }
    return u


def test_pareto_dominated_excluded():
    # A is strictly dominated by B on all objectives
    a = _make_universe("A", f1=0.3, recall=0.3, fpr=0.4, cost=200_000)
    b = _make_universe("B", f1=0.8, recall=0.8, fpr=0.1, cost=50_000)
    ranker = UniverseRanker()
    ids = ranker._pareto_frontier([a, b])
    assert "B" in ids
    assert "A" not in ids


def test_pareto_tradeoff_both_on_frontier():
    # A has better F1, B has lower cost — neither dominates
    a = _make_universe("A", f1=0.9, recall=0.9, fpr=0.2, cost=200_000)
    b = _make_universe("B", f1=0.5, recall=0.5, fpr=0.1, cost=10_000)
    ranker = UniverseRanker()
    ids = ranker._pareto_frontier([a, b])
    assert "A" in ids
    assert "B" in ids


def test_rank_assigns_ordinal(request):
    universes = [
        _make_universe("A", f1=0.9, recall=0.8, fpr=0.1, cost=100_000),
        _make_universe("B", f1=0.5, recall=0.4, fpr=0.3, cost=300_000),
        _make_universe("C", f1=0.7, recall=0.6, fpr=0.2, cost=200_000),
    ]
    ranker = UniverseRanker()
    ranked = ranker.rank(universes)
    ranks = [u.rank for u in ranked]
    assert sorted(ranks) == [1, 2, 3]


def test_pareto_metadata_in_metrics():
    universes = [
        _make_universe("A", f1=0.9, recall=0.8, fpr=0.1, cost=100_000),
        _make_universe("B", f1=0.5, recall=0.4, fpr=0.3, cost=300_000),
    ]
    ranker = UniverseRanker()
    ranker.rank(universes)
    for u in universes:
        assert "on_pareto_front" in u.metrics
        assert "rank_sensitivity" in u.metrics


def test_sensitivity_min_max_ranks():
    universes = [
        _make_universe("A", f1=0.9, recall=0.8, fpr=0.1, cost=100_000),
        _make_universe("B", f1=0.5, recall=0.4, fpr=0.3, cost=300_000),
        _make_universe("C", f1=0.7, recall=0.6, fpr=0.2, cost=200_000),
    ]
    ranker = UniverseRanker()
    ranker.rank(universes)
    for u in universes:
        s = u.metrics["rank_sensitivity"]
        assert s["min_rank"] <= s["max_rank"]
        assert 1 <= s["min_rank"] <= 3
