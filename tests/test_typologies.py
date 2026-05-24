import numpy as np
import pytest

from src.typologies.smurfing import SmurfingTypology
from src.typologies.layering import LayeringTypology
from src.typologies.structuring import StructuringTypology
from src.typologies.round_tripping import RoundTrippingTypology
from src.typologies.injector import TypologyInjector


@pytest.fixture
def bad_accounts(accounts):
    return accounts["account_id"].tolist()[:30]


def test_smurfing_injects_transactions(transactions, accounts, bad_accounts):
    typo = SmurfingTypology(rng=np.random.default_rng(0), n_scenarios=2, smurfs_per_scenario=4)
    result = typo.inject(transactions, accounts, bad_accounts)
    assert len(result) > len(transactions)
    illicit = result[result["is_illicit"]]
    assert (illicit["illicit_typology"] == "smurfing").all()


def test_smurfing_amounts_below_threshold(transactions, accounts, bad_accounts):
    typo = SmurfingTypology(rng=np.random.default_rng(0), n_scenarios=2, smurfs_per_scenario=4)
    result = typo.inject(transactions, accounts, bad_accounts)
    smurf_txns = result[result["illicit_typology"] == "smurfing"]
    assert (smurf_txns["amount"] < 10_100).all()


def test_layering_injects_transactions(transactions, accounts, bad_accounts):
    typo = LayeringTypology(rng=np.random.default_rng(0), n_chains=2, chain_length=4)
    result = typo.inject(transactions, accounts, bad_accounts)
    assert len(result) > len(transactions)


def test_structuring_injects_transactions(transactions, accounts, bad_accounts):
    typo = StructuringTypology(rng=np.random.default_rng(0), n_actors=3, txns_per_actor=5)
    result = typo.inject(transactions, accounts, bad_accounts)
    assert len(result) > len(transactions)


def test_round_tripping_injects_transactions(transactions, accounts, bad_accounts):
    typo = RoundTrippingTypology(rng=np.random.default_rng(0), n_cycles=2, intermediaries=3)
    result = typo.inject(transactions, accounts, bad_accounts)
    assert len(result) > len(transactions)


def test_injector_select_bad_actors(transactions, accounts, customers):
    injector = TypologyInjector(illicit_account_ratio=0.1, seed=0)
    bad = injector.select_bad_actors(accounts, customers)
    assert len(bad) >= 10
    assert all(acc in accounts["account_id"].values for acc in bad)


def test_injector_inject_all(transactions, accounts, customers):
    injector = TypologyInjector(illicit_account_ratio=0.1, seed=0)
    result = injector.inject_all(transactions, accounts, customers)
    assert result["is_illicit"].any()
    assert "illicit_typology" in result.columns
