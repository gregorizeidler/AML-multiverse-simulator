from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import BaseTypology


@dataclass
class LayeringTypology(BaseTypology):
    """
    Layering: illicit funds move through a chain of accounts in rapid succession
    to obscure the original source. Each hop slightly reduces the amount
    (simulating fees/skimming).
    """

    name: str = "layering"
    n_chains: int = 4
    chain_length: int = 6

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

        for chain_idx in range(self.n_chains):
            if len(bad_accounts) < self.chain_length:
                break

            chain = self.rng.choice(
                bad_accounts, size=self.chain_length, replace=False
            ).tolist()

            base_time = pd.Timestamp("2023-01-01") + pd.Timedelta(
                days=int(self.rng.integers(0, 340))
            )
            amount = self.rng.uniform(30_000, 150_000)

            for hop in range(self.chain_length - 1):
                src = chain[hop]
                dst = chain[hop + 1]
                amount *= self.rng.uniform(0.88, 0.99)  # skim each hop
                ts = base_time + pd.Timedelta(hours=int(self.rng.integers(1, 12)))
                base_time = ts

                src_country = _country(src)
                dst_country = _country(dst)

                new_rows.append(
                    {
                        "tx_id": f"LAYER_{chain_idx}_{hop:03d}",
                        "from_account": src,
                        "to_account": dst,
                        "amount": round(amount, 2),
                        "currency": "USD",
                        "tx_type": "transfer",
                        "channel": self.rng.choice(["mobile", "api", "web"]),
                        "timestamp": ts,
                        "from_country": src_country,
                        "to_country": dst_country,
                        "is_cross_border": src_country != dst_country,
                        "is_illicit": True,
                        "illicit_typology": self.name,
                    }
                )

        if not new_rows:
            return transactions

        injected = pd.DataFrame(new_rows)
        combined = pd.concat([transactions, injected], ignore_index=True)
        return combined.sort_values("timestamp").reset_index(drop=True)
