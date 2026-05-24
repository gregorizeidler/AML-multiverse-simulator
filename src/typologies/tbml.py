from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import BaseTypology

# Countries commonly involved in trade-based ML schemes
TBML_HIGH_RISK_COUNTRIES = ["CN", "AE", "TH", "MX", "PK", "NG", "VN", "BD"]
TBML_CLEAN_COUNTRIES = ["US", "GB", "DE", "NL", "SG"]


@dataclass
class TBMLTypology(BaseTypology):
    """
    Trade-Based Money Laundering (TBML) — estimated to represent
    80%+ of global ML volume (FATF Report 2022).

    Mechanism: Launderers manipulate trade invoice values to move
    value across borders without explicit wire transfers.

    We model two variants:
      A) Over-invoicing: buyer pays far above market value to exporter
         → exporter receives "clean" excess as profit
      B) Multiple invoicing: same shipment invoiced multiple times
         → creates paper trail for multiple payments

    In our financial model, this appears as:
      - Large transfers to high-risk trade corridors
      - Values clustered around "round" commercial amounts (multiples of $5k, $10k)
      - Rapid back-transfer of ~10-20% as "commission" or "rebate"
      - Multiple payers for same payee in short window (multiple invoicing)
    """

    name: str = "tbml"
    n_scenarios: int = 4
    min_shipment_value: float = 50_000
    max_shipment_value: float = 500_000

    def inject(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        bad_accounts: list[str],
    ) -> pd.DataFrame:
        new_rows = []
        acc_idx = accounts.set_index("account_id")

        for scenario_idx in range(self.n_scenarios):
            if len(bad_accounts) < 6:
                break

            # Exporter (receives over-invoiced payment)
            exporter = self.rng.choice(bad_accounts)
            # Multiple importers (payers) — multiple-invoicing variant
            n_importers = int(self.rng.integers(3, 7))
            importers = [
                a for a in self.rng.choice(bad_accounts, size=min(n_importers, len(bad_accounts)), replace=False)
                if a != exporter
            ]
            if not importers:
                continue

            # Commission receiver (receives kickback)
            kickback_dest = self.rng.choice(
                [a for a in bad_accounts if a not in [exporter] + importers[:2]]
                or bad_accounts
            )

            base_time = pd.Timestamp("2023-01-01") + pd.Timedelta(
                days=int(self.rng.integers(0, 340))
            )

            # ── Variant A: Over-invoicing payments ──────────────────────────
            # Real market value would be ~60-80% of the invoiced amount
            true_value = self.rng.uniform(self.min_shipment_value, self.max_shipment_value)
            # Over-invoice by 30-80%
            over_factor = self.rng.uniform(1.3, 1.8)
            invoice_value = round(true_value * over_factor / 1000) * 1000  # round to $1k

            exporter_country = acc_idx.loc[exporter, "country"] if exporter in acc_idx.index else "AE"
            if exporter_country not in TBML_HIGH_RISK_COUNTRIES:
                exporter_country = self.rng.choice(TBML_HIGH_RISK_COUNTRIES)

            for j, importer in enumerate(importers):
                importer_country = acc_idx.loc[importer, "country"] if importer in acc_idx.index else "US"
                # Each importer pays a share (multiple invoicing = paying full amount multiple times)
                share = invoice_value * self.rng.uniform(0.9, 1.0)
                payment_time = base_time + pd.Timedelta(days=int(self.rng.integers(0, 5)))

                new_rows.append({
                    "tx_id": f"TBML_{scenario_idx}_{j:03d}",
                    "from_account": importer,
                    "to_account": exporter,
                    "amount": round(share, 2),
                    "currency": "USD",
                    "tx_type": "payment",
                    "channel": "api",
                    "timestamp": payment_time,
                    "from_country": importer_country,
                    "to_country": exporter_country,
                    "is_cross_border": importer_country != exporter_country,
                    "is_illicit": True,
                    "illicit_typology": self.name,
                })

            # ── Variant B: Kickback / rebate ("commission" for over-payment) ──
            kickback_amount = round(invoice_value * self.rng.uniform(0.10, 0.25), 2)
            kickback_time = base_time + pd.Timedelta(days=int(self.rng.integers(7, 30)))
            kickback_country = acc_idx.loc[kickback_dest, "country"] if kickback_dest in acc_idx.index else "HK"

            new_rows.append({
                "tx_id": f"TBML_{scenario_idx}_KB",
                "from_account": exporter,
                "to_account": kickback_dest,
                "amount": kickback_amount,
                "currency": "USD",
                "tx_type": "transfer",
                "channel": "web",
                "timestamp": kickback_time,
                "from_country": exporter_country,
                "to_country": kickback_country,
                "is_cross_border": exporter_country != kickback_country,
                "is_illicit": True,
                "illicit_typology": self.name,
            })

        if not new_rows:
            return transactions

        injected = pd.DataFrame(new_rows)
        combined = pd.concat([transactions, injected], ignore_index=True)
        return combined.sort_values("timestamp").reset_index(drop=True)
