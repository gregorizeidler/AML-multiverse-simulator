from __future__ import annotations

import numpy as np
import pandas as pd

from .crypto_fiat import CryptoFiatTypology
from .layering import LayeringTypology
from .round_tripping import RoundTrippingTypology
from .shell_company import ShellCompanyTypology
from .smurfing import SmurfingTypology
from .structuring import StructuringTypology
from .tbml import TBMLTypology


class TypologyInjector:
    """
    Selects a pool of 'bad actor' accounts from high-risk customers and
    orchestrates injection of all four typologies into the transaction set.
    """

    def __init__(
        self,
        illicit_account_ratio: float = 0.05,
        seed: int = 42,
    ) -> None:
        self.illicit_account_ratio = illicit_account_ratio
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.bad_accounts: list[str] = []

    def select_bad_actors(
        self,
        accounts: pd.DataFrame,
        customers: pd.DataFrame,
    ) -> list[str]:
        """Prefer high-risk customers; fall back to random sample if needed."""
        high_risk_customers = customers[customers["risk_level"] == "high"][
            "customer_id"
        ].tolist()

        candidate_accounts = accounts[
            accounts["customer_id"].isin(high_risk_customers)
        ]["account_id"].tolist()

        n_bad = max(
            20,
            int(len(accounts) * self.illicit_account_ratio),
        )

        if len(candidate_accounts) >= n_bad:
            self.bad_accounts = self.rng.choice(
                candidate_accounts, size=n_bad, replace=False
            ).tolist()
        else:
            # Top up with random accounts
            remaining_accounts = accounts[
                ~accounts["account_id"].isin(candidate_accounts)
            ]["account_id"].tolist()
            top_up = n_bad - len(candidate_accounts)
            extra = self.rng.choice(
                remaining_accounts,
                size=min(top_up, len(remaining_accounts)),
                replace=False,
            ).tolist()
            self.bad_accounts = candidate_accounts + extra

        return self.bad_accounts

    def inject_all(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        customers: pd.DataFrame,
    ) -> pd.DataFrame:
        """Run all typology injectors sequentially and return augmented transactions."""
        bad_accounts = self.select_bad_actors(accounts, customers)

        typologies = [
            SmurfingTypology(
                rng=np.random.default_rng(self.seed + 1),
                n_scenarios=8,
                smurfs_per_scenario=6,
            ),
            LayeringTypology(
                rng=np.random.default_rng(self.seed + 2),
                n_chains=5,
                chain_length=5,
            ),
            StructuringTypology(
                rng=np.random.default_rng(self.seed + 3),
                n_actors=8,
                txns_per_actor=8,
            ),
            RoundTrippingTypology(
                rng=np.random.default_rng(self.seed + 4),
                n_cycles=4,
                intermediaries=4,
            ),
            TBMLTypology(
                rng=np.random.default_rng(self.seed + 5),
                n_scenarios=4,
            ),
            ShellCompanyTypology(
                rng=np.random.default_rng(self.seed + 6),
                n_scenarios=3,
                min_hops=3,
                max_hops=6,
            ),
            CryptoFiatTypology(
                rng=np.random.default_rng(self.seed + 7),
                n_scenarios=3,
            ),
        ]

        df = transactions.copy()
        for typology in typologies:
            df = typology.inject(df, accounts, bad_accounts)

        return df
