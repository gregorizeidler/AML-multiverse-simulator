import pandas as pd
import pytest

from src.data_generator.customers import generate_customers
from src.data_generator.accounts import generate_accounts
from src.data_generator.transactions import generate_transactions
from src.data_generator.fintech import SyntheticFintech


def test_generate_customers_shape():
    df = generate_customers(100, seed=1)
    assert len(df) == 100
    assert "customer_id" in df.columns
    assert "risk_level" in df.columns


def test_generate_customers_risk_levels():
    df = generate_customers(500, seed=1)
    assert set(df["risk_level"].unique()).issubset({"low", "medium", "high"})


def test_generate_accounts_shape(customers):
    accounts = generate_accounts(customers, seed=1)
    assert len(accounts) >= len(customers)
    assert "account_id" in accounts.columns
    assert "customer_id" in accounts.columns


def test_generate_accounts_customer_link(customers, accounts):
    assert set(accounts["customer_id"]).issubset(set(customers["customer_id"]))


def test_generate_transactions_shape(accounts):
    txns = generate_transactions(accounts, n_transactions=200, seed=1)
    assert len(txns) == 200
    assert "tx_id" in txns.columns
    assert "amount" in txns.columns


def test_generate_transactions_amounts_positive(transactions):
    assert (transactions["amount"] > 0).all()


def test_generate_transactions_no_self_loops(transactions):
    assert (transactions["from_account"] != transactions["to_account"]).all()


def test_synthetic_fintech_generate():
    fintech = SyntheticFintech(n_customers=50, n_transactions=200, seed=99).generate()
    assert fintech.customers is not None
    assert fintech.accounts is not None
    assert fintech.transactions is not None


def test_synthetic_fintech_summary():
    fintech = SyntheticFintech(n_customers=50, n_transactions=200, seed=99).generate()
    summary = fintech.summary
    assert summary["n_transactions"] == 200
    assert summary["n_customers"] == 50
