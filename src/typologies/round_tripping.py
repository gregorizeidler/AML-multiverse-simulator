from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import BaseTypology


@dataclass
class RoundTrippingTypology(BaseTypology):
    """
    Round-Tripping: funds leave an account, travel through a series of
    shell/intermediary accounts (often cross-border), and return to the
    originating account appearing as 'legitimate foreign investment'.
    """

    name: str = "round_tripping"
    n_cycles: int = 3
    intermediaries: int = 4

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

        high_risk_countries = ["NG", "VE", "IR", "KP", "MM"]

        for cycle_idx in range(self.n_cycles):
            required = self.intermediaries + 1
            if len(bad_accounts) < required:
                break

            participants = self.rng.choice(
                bad_accounts, size=required, replace=False
            ).tolist()
            origin = participants[0]
            chain = participants[1:] + [origin]  # returns to origin

            base_time = pd.Timestamp("2023-01-01") + pd.Timedelta(
                days=int(self.rng.integers(0, 300))
            )
            amount = self.rng.uniform(80_000, 500_000)
            country = _country(origin)

            for hop_idx, (src, dst) in enumerate(zip(participants, chain)):
                # Simulate cross-border legs through high-risk jurisdiction
                if hop_idx == 1:
                    src_country = self.rng.choice(high_risk_countries)
                    dst_country = self.rng.choice(high_risk_countries)
                else:
                    src_country = _country(src)
                    dst_country = _country(dst)

                amount *= self.rng.uniform(0.90, 1.05)  # slight variation each hop
                ts = base_time + pd.Timedelta(days=int(self.rng.integers(5, 30)))
                base_time = ts

                new_rows.append(
                    {
                        "tx_id": f"ROUND_{cycle_idx}_{hop_idx:03d}",
                        "from_account": src,
                        "to_account": dst,
                        "amount": round(amount, 2),
                        "currency": "USD",
                        "tx_type": "transfer",
                        "channel": "api",
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
