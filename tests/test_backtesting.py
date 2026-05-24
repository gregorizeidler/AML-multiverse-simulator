from pathlib import Path

import pytest

from src.backtesting.engine import BacktestingEngine
from src.backtesting.results import BacktestResults, WindowResult
from src.rule_engine.loader import load_universe_config


CONFIG_DIR = Path("config/universes")


@pytest.fixture
def config():
    path = CONFIG_DIR / "universe_balanced.yaml"
    if not path.exists():
        pytest.skip("Config not found")
    return load_universe_config(path)


def test_backtesting_engine_runs(config, transactions, accounts):
    engine = BacktestingEngine(window_days=90, min_transactions=5)
    results = engine.run(config, transactions, accounts)
    assert isinstance(results, BacktestResults)
    assert results.universe_id == config.id
    assert results.window_size_days == 90


def test_backtesting_windows_exist(config, transactions, accounts):
    engine = BacktestingEngine(window_days=90, min_transactions=5)
    results = engine.run(config, transactions, accounts)
    # Should produce at least one window for a year of data
    assert len(results.windows) >= 1


def test_backtesting_window_metrics(config, transactions, accounts):
    engine = BacktestingEngine(window_days=90, min_transactions=5)
    results = engine.run(config, transactions, accounts)
    for w in results.windows:
        assert isinstance(w, WindowResult)
        assert 0 <= w.f1 <= 1
        assert 0 <= w.recall <= 1
        assert w.n_transactions > 0


def test_backtesting_avg_f1(config, transactions, accounts):
    engine = BacktestingEngine(window_days=90, min_transactions=5)
    results = engine.run(config, transactions, accounts)
    assert 0 <= results.avg_f1 <= 1


def test_backtesting_to_dict(config, transactions, accounts):
    engine = BacktestingEngine(window_days=90, min_transactions=5)
    results = engine.run(config, transactions, accounts)
    d = results.to_dict()
    assert "universe_id" in d
    assert "avg_f1" in d
    assert "windows" in d
    assert isinstance(d["windows"], list)
