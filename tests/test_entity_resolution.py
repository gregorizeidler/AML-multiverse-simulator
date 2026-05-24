"""Tests for entity resolution."""
import pandas as pd
import pytest

from src.entity_resolution.resolver import EntityResolver, EntityGraph


@pytest.fixture
def accounts():
    return pd.DataFrame({
        "account_id":  ["ACC-1", "ACC-2", "ACC-3", "ACC-4", "ACC-5"],
        "customer_id": ["CUS-A", "CUS-A", "CUS-B", "CUS-C", "CUS-C"],
        "risk_level":  ["high", "low", "medium", "high", "medium"],
        "country":     ["US", "US", "DE", "MX", "MX"],
    })


@pytest.fixture
def customers():
    return pd.DataFrame({
        "customer_id": ["CUS-A", "CUS-B", "CUS-C"],
        "email":       ["alice@corp.com", "bob@gmail.com", "charlie@corp.com"],
        "phone":       ["555-1234", "555-9999", "555-1234"],  # Charlie shares prefix with Alice
    })


def test_same_customer_linked(accounts, customers):
    graph = EntityResolver().resolve(accounts, customers)
    # ACC-1 and ACC-2 share CUS-A → must be same entity
    assert graph.account_to_entity["ACC-1"] == graph.account_to_entity["ACC-2"]


def test_different_customer_different_entity(accounts, customers):
    graph = EntityResolver().resolve(accounts, customers)
    assert graph.account_to_entity["ACC-1"] != graph.account_to_entity["ACC-3"]


def test_entity_risk_propagation(accounts, customers):
    graph = EntityResolver().resolve(accounts, customers)
    # CUS-A has one high-risk account → entity risk should be > 0.5
    ent = graph.account_to_entity["ACC-1"]
    assert graph.entity_risk[ent] > 0.5


def test_entity_graph_to_dict(accounts, customers):
    graph = EntityResolver().resolve(accounts, customers)
    d = graph.to_dict()
    assert "n_entities" in d
    assert "n_accounts_linked" in d
    assert "entities_with_multiple_accounts" in d


def test_enrich_transactions(accounts, customers):
    graph = EntityResolver().resolve(accounts, customers)
    txns = pd.DataFrame({
        "tx_id": ["T1", "T2"],
        "from_account": ["ACC-1", "ACC-3"],
        "amount": [1000, 2000],
    })
    enriched = graph.enrich_transactions(txns)
    assert "from_entity" in enriched.columns
    assert "from_entity_risk" in enriched.columns
    assert enriched["from_entity_risk"].notna().all()


def test_n_entities_leq_n_accounts(accounts, customers):
    graph = EntityResolver().resolve(accounts, customers)
    assert graph.n_entities <= len(accounts)
