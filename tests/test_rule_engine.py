from pathlib import Path

import pandas as pd
import pytest

from src.rule_engine.loader import load_universe_config, load_all_configs
from src.rule_engine.evaluator import RuleEvaluator
from src.rule_engine.alert_manager import AlertManager

CONFIG_DIR = Path("config/universes")


def test_load_single_config():
    path = CONFIG_DIR / "universe_balanced.yaml"
    if not path.exists():
        pytest.skip("Config file not found")
    cfg = load_universe_config(path)
    assert cfg.id == "universe_balanced"
    assert len(cfg.rules) > 0


def test_load_all_configs():
    if not CONFIG_DIR.exists():
        pytest.skip("Config directory not found")
    configs = load_all_configs(CONFIG_DIR)
    assert len(configs) >= 5  # currently 7 (added GNN and ML universes)


def test_rule_evaluator_adds_alert_score():
    path = CONFIG_DIR / "universe_balanced.yaml"
    if not path.exists():
        pytest.skip("Config file not found")
    cfg = load_universe_config(path)
    df = pd.DataFrame(
        {
            "tx_id": ["T001", "T002"],
            "amount": [20000, 100],
            "tx_count_1h": [10, 1],
            "amount_24h": [50000, 200],
            "unique_counterparties_7d": [15, 2],
            "is_round_amount": [0, 0],
            "is_cross_border": [0, 0],
            "days_since_last_tx": [10, 5],
            "betweenness_centrality": [0.0, 0.0],
            "amount_zscore": [6.0, 0.5],
            "peer_group_deviation": [3.5, 0.2],
            "behavioral_anomaly_score": [0.8, 0.1],
        }
    )
    evaluator = RuleEvaluator(cfg)
    result = evaluator.evaluate(df)
    assert "alert_score" in result.columns
    assert "is_alerted" in result.columns
    assert result.loc[0, "alert_score"] > result.loc[1, "alert_score"]


def test_alert_manager_builds_alerts():
    path = CONFIG_DIR / "universe_conservative.yaml"
    if not path.exists():
        pytest.skip("Config file not found")
    cfg = load_universe_config(path)
    df = pd.DataFrame(
        {
            "tx_id": ["T001"],
            "from_account": ["A001"],
            "to_account": ["A002"],
            "amount": [20000],
            "timestamp": pd.to_datetime(["2023-06-01"]),
            "alert_score": [10.0],
            "is_alerted": [True],
            "is_high_risk": [True],
            "is_illicit": [True],
            "illicit_typology": ["smurfing"],
            "rule_R001_hit": [True],
            "rule_R002_hit": [False],
        }
    )
    mgr = AlertManager(cfg)
    alerts = mgr.build_alerts(df)
    assert len(alerts) == 1
    assert "fired_rules" in alerts.columns
