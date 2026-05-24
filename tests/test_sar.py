import pandas as pd
import pytest

from src.sar.generator import SARGenerator
from src.sar.report import SARReport, SARSubject


def _make_alerts():
    return pd.DataFrame(
        {
            "tx_id": [f"T{i:04d}" for i in range(20)],
            "from_account": ["A001"] * 10 + ["A002"] * 10,
            "to_account": ["A003"] * 20,
            "amount": [9500.0] * 20,
            "timestamp": pd.date_range("2023-03-01", periods=20, freq="1h"),
            "alert_score": [5.5] * 20,
            "alert_level": ["high"] * 15 + ["critical"] * 5,
            "illicit_typology": ["smurfing"] * 20,
            "is_illicit": [True] * 20,
            "from_country": ["US"] * 20,
            "to_country": ["US"] * 20,
        }
    )


def _make_evaluated():
    return pd.DataFrame(
        {
            "tx_id": [f"T{i:04d}" for i in range(20)],
            "is_illicit": [True] * 20,
            "illicit_typology": ["smurfing"] * 20,
        }
    )


def test_sar_generator_produces_reports():
    gen = SARGenerator(universe_id="universe_balanced", min_cluster_size=3)
    alerts = _make_alerts()
    evaluated = _make_evaluated()
    reports = gen.generate_all(alerts, evaluated)
    assert len(reports) >= 1
    report = reports[0]
    assert isinstance(report, SARReport)
    assert report.sar_id.startswith("SAR-")
    assert report.primary_typology == "smurfing"


def test_sar_report_to_dict():
    gen = SARGenerator(universe_id="universe_test", min_cluster_size=3)
    alerts = _make_alerts()
    evaluated = _make_evaluated()
    reports = gen.generate_all(alerts, evaluated)
    d = reports[0].to_dict()
    assert "sar_id" in d
    assert "narrative" in d
    assert "financial_activity" in d
    assert "recommended_actions" in d
    assert d["financial_activity"]["n_transactions"] > 0


def test_sar_empty_alerts():
    gen = SARGenerator(universe_id="test")
    reports = gen.generate_all(pd.DataFrame(), pd.DataFrame())
    assert reports == []


def test_sar_narrative_contains_universe():
    gen = SARGenerator(universe_id="universe_graph_enhanced")
    alerts = _make_alerts()
    evaluated = _make_evaluated()
    reports = gen.generate_all(alerts, evaluated)
    assert "universe_graph_enhanced" in reports[0].narrative
