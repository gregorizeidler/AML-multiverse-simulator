from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import BaseTypology

# Crypto-friendly / lax-regulation jurisdictions
CRYPTO_JURISDICTIONS = ["MT", "SV", "AE", "SG", "CH", "BS"]
EXCHANGE_ACCOUNTS_PREFIX = "EXCH"


@dataclass
class CryptoFiatTypology(BaseTypology):
    """
    Crypto-to-Fiat Conversion Laundering.

    Mechanism:
      Phase 1 — Aggregation: dirty fiat funds collected from multiple sources
      Phase 2 — Crypto exchange: aggregated amount sent to exchange account
                 (represented as an account in our model)
      Phase 3 — Mixing delay: funds held at exchange for 3-14 days
                 (mimicking on-chain mixing/tumbling)
      Phase 4 — Off-ramp: "clean" fiat proceeds arrive from different exchange
                 account, often in a different currency/jurisdiction

    Financial signature:
      - Large one-directional inflows to exchange-like accounts (round amounts)
      - Temporal gap before corresponding outflows
      - Outflow accounts are unrelated to inflow accounts
      - Cross-border from crypto-friendly jurisdictions
      - Amount slightly different from inflow (exchange fees 0.5-2%)
    """

    name: str = "crypto_fiat"
    n_scenarios: int = 3
    aggregation_sources: int = 5
    min_amount: float = 20_000
    max_amount: float = 300_000
    exchange_fee_rate: float = 0.015  # 1.5% exchange fee

    def inject(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        bad_accounts: list[str],
    ) -> pd.DataFrame:
        new_rows = []
        acc_idx = accounts.set_index("account_id")

        for scenario_idx in range(self.n_scenarios):
            n_sources = int(self.rng.integers(3, self.aggregation_sources + 1))
            needed = n_sources + 2  # sources + exchange_in + destination
            if len(bad_accounts) < needed:
                break

            selected = list(self.rng.choice(bad_accounts, size=needed, replace=False))
            sources = selected[:n_sources]
            exchange_in_account = selected[n_sources]
            destination_account = selected[n_sources + 1]

            total_amount = self.rng.uniform(self.min_amount, self.max_amount)
            # Round to nearest $1000 (crypto exchange typical behavior)
            total_amount = round(total_amount / 1000) * 1000

            base_time = pd.Timestamp("2023-01-01") + pd.Timedelta(
                days=int(self.rng.integers(0, 300))
            )

            # ── Phase 1: Aggregation → Exchange ──────────────────────────────
            exch_country = self.rng.choice(CRYPTO_JURISDICTIONS)

            for j, src in enumerate(sources):
                share = round(total_amount / n_sources * self.rng.uniform(0.8, 1.2), 2)
                src_country = acc_idx.loc[src, "country"] if src in acc_idx.index else "US"
                agg_time = base_time + pd.Timedelta(hours=int(self.rng.integers(0, 48)))

                new_rows.append({
                    "tx_id": f"CF_{scenario_idx}_AGG_{j:03d}",
                    "from_account": src,
                    "to_account": exchange_in_account,
                    "amount": share,
                    "currency": "USD",
                    "tx_type": "transfer",
                    "channel": "api",
                    "timestamp": agg_time,
                    "from_country": src_country,
                    "to_country": exch_country,
                    "is_cross_border": src_country != exch_country,
                    "is_illicit": True,
                    "illicit_typology": self.name,
                })

            # ── Phase 3 → 4: Off-ramp (after mixing delay) ───────────────────
            mixing_delay_days = int(self.rng.integers(3, 15))
            offramp_time = base_time + pd.Timedelta(days=mixing_delay_days)

            # Net of exchange fee
            clean_amount = round(total_amount * (1 - self.exchange_fee_rate), 2)
            dest_country = acc_idx.loc[destination_account, "country"] if destination_account in acc_idx.index else "US"

            # Off-ramp comes from a *different* exchange jurisdiction
            offramp_country = self.rng.choice(
                [j for j in CRYPTO_JURISDICTIONS if j != exch_country] or CRYPTO_JURISDICTIONS
            )

            new_rows.append({
                "tx_id": f"CF_{scenario_idx}_OFFRAMP",
                "from_account": exchange_in_account,
                "to_account": destination_account,
                "amount": clean_amount,
                "currency": "USD",
                "tx_type": "payment",
                "channel": "web",
                "timestamp": offramp_time,
                "from_country": offramp_country,
                "to_country": dest_country,
                "is_cross_border": offramp_country != dest_country,
                "is_illicit": True,
                "illicit_typology": self.name,
            })

        if not new_rows:
            return transactions

        injected = pd.DataFrame(new_rows)
        combined = pd.concat([transactions, injected], ignore_index=True)
        return combined.sort_values("timestamp").reset_index(drop=True)
