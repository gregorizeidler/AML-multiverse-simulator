"""Tests for the LLM module (heuristic mode — no API key required)."""

import pytest
from src.llm.client import LLMClient, get_llm_client
from src.llm.sar_writer import LLMSARWriter
from src.llm.explainer import TransactionExplainer


@pytest.fixture
def llm_client():
    """Force heuristic mode by passing no API key."""
    client = LLMClient(model="gpt-4o-mini")
    client._mode = "heuristic"
    client._openai_client = None
    return client


def test_client_heuristic_mode(llm_client):
    assert llm_client.mode == "heuristic"
    assert llm_client.is_real_llm is False


def test_client_sar_heuristic(llm_client):
    result = llm_client.complete("You are an AML analyst.", "Write a SAR narrative")
    assert isinstance(result, str)
    assert len(result) > 20


def test_client_explain_heuristic(llm_client):
    result = llm_client.complete("system", "explain why this amount was flagged")
    assert "flagged" in result.lower() or "transaction" in result.lower()


def test_sar_writer_heuristic(llm_client):
    writer = LLMSARWriter(client=llm_client)
    narrative = writer.write_narrative(
        typology="smurfing",
        total_amount=85000,
        n_transactions=12,
        subjects=[{"account_id": "ACC-001", "role": "primary", "transaction_count": 12,
                   "total_amount": 85000, "countries": ["US", "MX"]}],
        activity_start="2024-01-01",
        activity_end="2024-01-31",
        avg_score=4.2,
        universe_id="universe_conservative",
    )
    assert isinstance(narrative, str)
    assert len(narrative) > 50


def test_explainer_heuristic(llm_client):
    explainer = TransactionExplainer(client=llm_client)
    tx = {
        "tx_id": "TX-001",
        "amount": 9500.0,
        "alert_score": 3.7,
        "is_illicit": True,
        "illicit_typology": "structuring",
        "amount_zscore": 2.8,
    }
    result = explainer.explain_alert(tx, fired_rules=["high_velocity", "amount_threshold"])
    assert isinstance(result, str)
    assert len(result) > 20
