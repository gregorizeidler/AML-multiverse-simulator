from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import BaseTypology

CTR_THRESHOLD = 10_000.0


@dataclass
class StructuringTypology(BaseTypology):
    """
    Structuring (aka 'structuring to avoid reporting'): a single account makes
    multiple deposits or withdrawals just below the CTR threshold over several
    days to avoid triggering Currency Transaction Reports.
    """

    name: str = "structuring"
    n_actors: int = 6
    txns_per_actor: int = 10

    def inject(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        bad_accounts: list[str],
    ) -> pd.DataFrame:
        new_rows = []
        acc_index = accounts.set_index("account_id")

        def _country(acc_id: str) -> str:
            try:
                return acc_index.loc[acc_id, "country"]
            except KeyError:
                return "US"

        actors = self.rng.choice(
            bad_accounts,
            size=min(self.n_actors, len(bad_accounts)),
            replace=False,
        ).tolist()

        for actor_idx, actor in enumerate(actors):
            base_time = pd.Timestamp("2023-01-01") + pd.Timedelta(
                days=int(self.rng.integers(0, 330))
            )
            country = _country(actor)
            counterparties = [
                a for a in bad_accounts if a != actor
            ]

            for i in range(self.txns_per_actor):
                amount = CTR_THRESHOLD - self.rng.uniform(100, 900)
                ts = base_time + pd.Timedelta(
                    hours=int(self.rng.integers(12, 48))
                )
                base_time = ts

                cp = self.rng.choice(counterparties) if counterparties else actor
                cp_country = _country(cp)

                new_rows.append(
                    {
                        "tx_id": f"STRUCT_{actor_idx}_{i:03d}",
                        "from_account": actor,
                        "to_account": cp,
                        "amount": round(amount, 2),
                        "currency": "USD",
                        "tx_type": "deposit",
                        "channel": "branch",
                        "timestamp": ts,
                        "from_country": country,
                        "to_country": cp_country,
                        "is_cross_border": country != cp_country,
                        "is_illicit": True,
                        "illicit_typology": self.name,
                    }
                )

        if not new_rows:
            return transactions

        injected = pd.DataFrame(new_rows)
        combined = pd.concat([transactions, injected], ignore_index=True)
        return combined.sort_values("timestamp").reset_index(drop=True)
