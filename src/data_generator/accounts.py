from __future__ import annotations

import numpy as np
import pandas as pd

ACCOUNT_TYPES = ["checking", "savings", "business", "investment"]
ACCOUNT_TYPE_WEIGHTS = [0.50, 0.25, 0.18, 0.07]

CURRENCIES = ["USD", "USD", "USD", "USD", "EUR", "GBP", "CAD"]


def generate_accounts(customers: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(customers)

    # Most customers have 1 account; some have 2-3
    account_counts = rng.choice([1, 2, 3], size=n, p=[0.70, 0.22, 0.08])

    records = []
    acc_idx = 0
    for _, customer in customers.iterrows():
        n_accounts = account_counts[_ if isinstance(_, int) else 0]
        for j in range(n_accounts):
            acc_type = rng.choice(ACCOUNT_TYPES, p=ACCOUNT_TYPE_WEIGHTS)
            opened_at = customer["created_at"] + pd.Timedelta(
                days=int(rng.integers(0, 180))
            )

            # Balance correlated with income and risk
            income = customer["annual_income"]
            balance_multiplier = rng.uniform(0.05, 0.8)
            balance = income * balance_multiplier

            records.append(
                {
                    "account_id": f"A{acc_idx:07d}",
                    "customer_id": customer["customer_id"],
                    "account_type": acc_type,
                    "currency": rng.choice(CURRENCIES),
                    "balance": round(balance, 2),
                    "opened_at": opened_at,
                    "country": customer["country"],
                    "risk_level": customer["risk_level"],
                    "is_active": rng.random() > 0.05,
                }
            )
            acc_idx += 1

    return pd.DataFrame(records)
