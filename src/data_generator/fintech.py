from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .accounts import generate_accounts
from .customers import generate_customers
from .transactions import generate_transactions


@dataclass
class SyntheticFintech:
    """Orchestrates generation of a complete synthetic fintech dataset."""

    n_customers: int = 2000
    n_transactions: int = 20000
    seed: int = 42
    start_date: str = "2023-01-01"
    end_date: str = "2024-01-01"

    customers: pd.DataFrame = field(default=None, init=False, repr=False)
    accounts: pd.DataFrame = field(default=None, init=False, repr=False)
    transactions: pd.DataFrame = field(default=None, init=False, repr=False)

    def generate(self) -> "SyntheticFintech":
        self.customers = generate_customers(self.n_customers, seed=self.seed)
        self.accounts = generate_accounts(self.customers, seed=self.seed)
        self.transactions = generate_transactions(
            self.accounts,
            n_transactions=self.n_transactions,
            start_date=self.start_date,
            end_date=self.end_date,
            seed=self.seed,
        )
        return self

    def save(self, output_dir: str | Path) -> None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.customers.to_parquet(output_dir / "customers.parquet", index=False)
        self.accounts.to_parquet(output_dir / "accounts.parquet", index=False)
        self.transactions.to_parquet(output_dir / "transactions.parquet", index=False)

    @classmethod
    def load(cls, data_dir: str | Path) -> "SyntheticFintech":
        data_dir = Path(data_dir)
        instance = cls.__new__(cls)
        instance.customers = pd.read_parquet(data_dir / "customers.parquet")
        instance.accounts = pd.read_parquet(data_dir / "accounts.parquet")
        instance.transactions = pd.read_parquet(data_dir / "transactions.parquet")
        return instance

    @property
    def summary(self) -> dict:
        return {
            "n_customers": len(self.customers),
            "n_accounts": len(self.accounts),
            "n_transactions": len(self.transactions),
            "illicit_transactions": int(self.transactions["is_illicit"].sum()),
            "illicit_ratio": round(
                self.transactions["is_illicit"].mean(), 4
            ),
            "date_range": {
                "start": str(self.transactions["timestamp"].min()),
                "end": str(self.transactions["timestamp"].max()),
            },
        }
