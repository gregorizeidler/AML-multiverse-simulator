"""Tests for the 3 new typologies: TBML, Shell Company, Crypto-Fiat."""
import numpy as np
import pandas as pd
import pytest

from src.typologies.tbml import TBMLTypology
from src.typologies.shell_company import ShellCompanyTypology
from src.typologies.crypto_fiat import CryptoFiatTypology


@pytest.fixture
def base_df():
    return pd.DataFrame({
        "tx_id": [f"T{i}" for i in range(20)],
        "from_account": [f"ACC-{i}" for i in range(20)],
        "to_account": [f"ACC-{(i+1)%20}" for i in range(20)],
        "amount": np.ones(20) * 1000,
        "currency": "USD",
        "tx_type": "transfer",
        "channel": "web",
        "timestamp": pd.date_range("2023-01-01", periods=20, freq="h"),
        "from_country": "US",
        "to_country": "US",
        "is_cross_border": False,
        "is_illicit": False,
        "illicit_typology": None,
    })


@pytest.fixture
def accounts():
    return pd.DataFrame({
        "account_id": [f"ACC-{i}" for i in range(30)],
        "customer_id": [f"CUS-{i//3}" for i in range(30)],
        "country": ["US", "AE", "MX", "CN", "DE"] * 6,
        "risk_level": ["high", "medium", "low"] * 10,
    })


@pytest.fixture
def bad_accounts():
    return [f"ACC-{i}" for i in range(20)]


def test_tbml_injects_rows(base_df, accounts, bad_accounts):
    t = TBMLTypology(rng=np.random.default_rng(0), n_scenarios=2)
    result = t.inject(base_df, accounts, bad_accounts)
    illicit = result[result["is_illicit"]]
    assert len(illicit) > 0
    assert (illicit["illicit_typology"] == "tbml").all()


def test_tbml_cross_border(base_df, accounts, bad_accounts):
    t = TBMLTypology(rng=np.random.default_rng(42), n_scenarios=2)
    result = t.inject(base_df, accounts, bad_accounts)
    illicit = result[result["is_illicit"]]
    # TBML should include some cross-border transactions
    assert illicit["is_cross_border"].any()


def test_shell_company_injects_chain(base_df, accounts, bad_accounts):
    t = ShellCompanyTypology(rng=np.random.default_rng(0), n_scenarios=2, min_hops=3)
    result = t.inject(base_df, accounts, bad_accounts)
    illicit = result[result["is_illicit"]]
    assert len(illicit) >= 3  # at least one chain
    assert (illicit["illicit_typology"] == "shell_company").all()


def test_shell_company_amount_decreases(base_df, accounts, bad_accounts):
    t = ShellCompanyTypology(rng=np.random.default_rng(0), n_scenarios=1, min_hops=4, max_hops=4)
    result = t.inject(base_df, accounts, bad_accounts)
    illicit = result[result["illicit_typology"] == "shell_company"].sort_values("timestamp")
    if len(illicit) >= 2:
        # Each hop amount ≤ previous (skim effect)
        amounts = illicit["amount"].values
        assert amounts[-1] <= amounts[0]


def test_crypto_fiat_injects(base_df, accounts, bad_accounts):
    t = CryptoFiatTypology(rng=np.random.default_rng(0), n_scenarios=2)
    result = t.inject(base_df, accounts, bad_accounts)
    illicit = result[result["is_illicit"]]
    assert len(illicit) > 0
    assert (illicit["illicit_typology"] == "crypto_fiat").all()


def test_crypto_fiat_offramp_delay(base_df, accounts, bad_accounts):
    t = CryptoFiatTypology(rng=np.random.default_rng(42), n_scenarios=1)
    result = t.inject(base_df, accounts, bad_accounts)
    cf = result[result["illicit_typology"] == "crypto_fiat"].sort_values("timestamp")
    if len(cf) >= 2:
        # Off-ramp must be after aggregation
        assert cf.iloc[-1]["timestamp"] > cf.iloc[0]["timestamp"]
