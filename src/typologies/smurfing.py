from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import BaseTypology

REPORTING_THRESHOLD = 10_000.0


@dataclass
class SmurfingTypology(BaseTypology):
    """
    Smurfing: a large illicit amount is broken into many small transactions,
    each just below the regulatory reporting threshold ($10,000), sent rapidly
    from multiple accounts to a central destination.
    """

    name: str = "smurfing"
    n_scenarios: int = 5
    smurfs_per_scenario: int = 8

    def inject(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        bad_accounts: list[str],
    ) -> pd.DataFrame:
        new_rows = []
        account_pool = bad_accounts.copy()

        for scenario_idx in range(self.n_scenarios):
            if len(account_pool) < self.smurfs_per_scenario + 1:
                break

            # Pick a destination (aggregator) and several source smurfs
            dest = self.rng.choice(account_pool)
            sources = self.rng.choice(
                [a for a in account_pool if a != dest],
                size=self.smurfs_per_scenario,
                replace=False,
            ).tolist()

            # Random point in time for the burst
            base_time = pd.Timestamp("2023-01-01") + pd.Timedelta(
                days=int(self.rng.integers(0, 360))
            )

            total_illicit = self.rng.uniform(50_000, 200_000)
            smurf_amount = min(
                REPORTING_THRESHOLD - self.rng.uniform(100, 800),
                total_illicit / self.smurfs_per_scenario,
            )

            dest_country = accounts.set_index("account_id").loc[dest, "country"] if dest in accounts["account_id"].values else "US"

            for i, src in enumerate(sources):
                src_country = accounts.set_index("account_id").loc[src, "country"] if src in accounts["account_id"].values else "US"
                ts = base_time + pd.Timedelta(minutes=int(self.rng.integers(1, 30)))
                new_rows.append(
                    {
                        "tx_id": f"SMURF_{scenario_idx}_{i:03d}",
                        "from_account": src,
                        "to_account": dest,
                        "amount": round(smurf_amount + self.rng.uniform(-200, 200), 2),
                        "currency": "USD",
                        "tx_type": "transfer",
                        "channel": "mobile",
                        "timestamp": ts,
                        "from_country": src_country,
                        "to_country": dest_country,
                        "is_cross_border": src_country != dest_country,
                        "is_illicit": True,
                        "illicit_typology": self.name,
                    }
                )

        if not new_rows:
            return transactions

        injected = pd.DataFrame(new_rows)
        combined = pd.concat([transactions, injected], ignore_index=True)
        combined = combined.sort_values("timestamp").reset_index(drop=True)
        return combined
