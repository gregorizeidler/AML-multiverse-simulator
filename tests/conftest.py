"""Shared fixtures for all test modules."""
import pytest
import numpy as np
import pandas as pd

from src.data_generator.customers import generate_customers
from src.data_generator.accounts import generate_accounts
from src.data_generator.transactions import generate_transactions


@pytest.fixture(scope="session")
def customers():
    return generate_customers(200, seed=0)


@pytest.fixture(scope="session")
def accounts(customers):
    return generate_accounts(customers, seed=0)


@pytest.fixture(scope="session")
def transactions(accounts):
    return generate_transactions(accounts, n_transactions=500, seed=0)


@pytest.fixture(scope="session")
def rng():
    return np.random.default_rng(0)
