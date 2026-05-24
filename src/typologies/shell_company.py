from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import BaseTypology

OFFSHORE_JURISDICTIONS = ["KY", "VG", "PA", "LU", "LI", "MC", "BS", "BZ"]


@dataclass
class ShellCompanyTypology(BaseTypology):
    """
    Shell Company / Corporate Layering.

    Mechanism: funds move through a chain of legally-distinct but
    beneficially-owned shell companies across multiple jurisdictions.
    Each shell "earns" a management or consulting fee before passing
    the net amount to the next layer.

    Financial signature:
      - N sequential transfers (hops) — each to a different account
      - Each hop moves slightly less (management fee / skim)
      - Jurisdictions jump through known offshore secrecy havens
      - Time gaps of days-to-weeks between hops (mimicking incorporation/transfer delays)
      - Final destination often receives a "dividend" or "loan repayment"
    """

    name: str = "shell_company"
    n_scenarios: int = 3
    min_hops: int = 3
    max_hops: int = 6
    skim_rate: float = 0.08   # each shell keeps ~8% as "fee"
    initial_min: float = 100_000
    initial_max: float = 1_000_000

    def inject(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        bad_accounts: list[str],
    ) -> pd.DataFrame:
        new_rows = []
        acc_idx = accounts.set_index("account_id")

        for scenario_idx in range(self.n_scenarios):
            n_hops = int(self.rng.integers(self.min_hops, self.max_hops + 1))
            if len(bad_accounts) < n_hops + 1:
                break

            chain = list(self.rng.choice(bad_accounts, size=n_hops + 1, replace=False))
            initial_amount = self.rng.uniform(self.initial_min, self.initial_max)
            amount = initial_amount

            # Stagger start date to spread activity across the year
            base_time = pd.Timestamp("2023-01-01") + pd.Timedelta(
                days=int(self.rng.integers(0, 200))
            )

            for hop_idx in range(n_hops):
                src = chain[hop_idx]
                dst = chain[hop_idx + 1]

                src_country = acc_idx.loc[src, "country"] if src in acc_idx.index else "US"
                dst_country = (
                    self.rng.choice(OFFSHORE_JURISDICTIONS)
                    if hop_idx < n_hops - 1
                    else (acc_idx.loc[dst, "country"] if dst in acc_idx.index else "US")
                )

                # Time delay between hops: 2–21 days (simulates corporate processing)
                delay_days = int(self.rng.integers(2, 22))
                tx_time = base_time + pd.Timedelta(days=delay_days * hop_idx)

                # Shell retains the "fee" — amount decreases each hop
                fee = amount * self.rng.uniform(self.skim_rate * 0.5, self.skim_rate * 1.5)
                net_forward = round(amount - fee, 2)

                tx_type = "transfer" if hop_idx < n_hops - 1 else "payment"

                new_rows.append({
                    "tx_id": f"SHELL_{scenario_idx}_{hop_idx:03d}",
                    "from_account": src,
                    "to_account": dst,
                    "amount": round(net_forward, 2),
                    "currency": "USD",
                    "tx_type": tx_type,
                    "channel": "api",
                    "timestamp": tx_time,
                    "from_country": src_country,
                    "to_country": dst_country,
                    "is_cross_border": src_country != dst_country,
                    "is_illicit": True,
                    "illicit_typology": self.name,
                })

                amount = net_forward

        if not new_rows:
            return transactions

        injected = pd.DataFrame(new_rows)
        combined = pd.concat([transactions, injected], ignore_index=True)
        return combined.sort_values("timestamp").reset_index(drop=True)
