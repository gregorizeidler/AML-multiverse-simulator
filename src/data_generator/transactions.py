from __future__ import annotations

import numpy as np
import pandas as pd

TX_TYPES = ["transfer", "deposit", "withdrawal", "payment", "refund"]
TX_TYPE_WEIGHTS = [0.35, 0.25, 0.20, 0.15, 0.05]

CHANNELS = ["mobile", "web", "atm", "branch", "api"]
CHANNEL_WEIGHTS = [0.40, 0.30, 0.15, 0.10, 0.05]

# Business-hours weight per hour (0-23): peaks at 9-11am and 2-4pm
_HOUR_WEIGHTS = np.array([
    0.3, 0.2, 0.1, 0.1, 0.1, 0.2,   # 0-5  (night)
    0.5, 1.2, 2.5, 3.8, 4.0, 3.5,   # 6-11 (morning peak)
    3.0, 3.2, 3.8, 3.5, 2.8, 2.2,   # 12-17 (afternoon peak)
    1.8, 1.5, 1.2, 0.9, 0.6, 0.4,   # 18-23 (evening)
])
_HOUR_WEIGHTS /= _HOUR_WEIGHTS.sum()


def _power_law_account_weights(n: int, alpha: float = 1.5) -> np.ndarray:
    """
    Preferential-attachment weight: P(account i sends) ∝ i^(-alpha).
    Creates a power-law degree distribution mimicking real payment networks
    where a small fraction of accounts drives most transaction volume.
    """
    ranks = np.arange(1, n + 1, dtype=float)
    weights = ranks ** (-alpha)
    return weights / weights.sum()


def _business_timestamp(
    n: int,
    start_ts: pd.Timestamp,
    span_seconds: int,
    rng: np.random.Generator,
) -> pd.Series:
    """
    Generate timestamps with realistic circadian rhythm:
    - Cluster around business hours (9am-5pm)
    - Lower volume on weekends (~40% of weekday)
    """
    raw_seconds = rng.integers(0, span_seconds, size=n)
    base = start_ts + pd.to_timedelta(raw_seconds, unit="s")

    # Resample hour of day according to business-hours weights
    hours = rng.choice(24, size=n, p=_HOUR_WEIGHTS)
    # Weekend dampening: Saturday=5, Sunday=6 → 40% chance to keep, else shift to Monday
    is_weekend = base.dayofweek >= 5
    keep_weekend = rng.random(n) < 0.40
    shift_to_monday = is_weekend & ~keep_weekend
    base = base + pd.to_timedelta(
        np.where(shift_to_monday, (7 - base.dayofweek) % 7, 0), unit="D"
    )

    # Apply hour-of-day distribution
    base = base.normalize() + pd.to_timedelta(hours, unit="h")
    base += pd.to_timedelta(rng.integers(0, 3600, size=n), unit="s")
    return base


def generate_transactions(
    accounts: pd.DataFrame,
    n_transactions: int,
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01",
    seed: int = 42,
    power_law_alpha: float = 1.5,
) -> pd.DataFrame:
    """
    Generates synthetic transactions with:
    - Power-law sender distribution (preferential attachment)
    - Receiver skewed toward high-degree accounts (realistic hub behavior)
    - Business-hours timestamp clustering
    - Log-normal amount distribution
    - Balance-aware clipping (rough cap per account income)
    """
    rng = np.random.default_rng(seed)
    account_ids = accounts["account_id"].tolist()
    n_accounts = len(account_ids)

    # Shuffle once so power-law doesn't always favor ACC-0001
    rng.shuffle(account_ids)

    # Power-law weights for sender selection
    send_weights = _power_law_account_weights(n_accounts, alpha=power_law_alpha)

    # Receiver weights: slightly different alpha to create asymmetric graph
    recv_weights = _power_law_account_weights(n_accounts, alpha=power_law_alpha * 0.8)
    recv_weights = recv_weights[::-1]  # flip so hubs are different accounts

    src_indices = rng.choice(n_accounts, size=n_transactions, p=send_weights)
    dst_indices = rng.choice(n_accounts, size=n_transactions, p=recv_weights)

    # Avoid self-transfers
    same_mask = src_indices == dst_indices
    dst_indices[same_mask] = (dst_indices[same_mask] + 1) % n_accounts

    src_accounts = [account_ids[i] for i in src_indices]
    dst_accounts = [account_ids[i] for i in dst_indices]

    # Timestamps with business-hour clustering
    start_ts = pd.Timestamp(start_date)
    end_ts   = pd.Timestamp(end_date)
    span_seconds = int((end_ts - start_ts).total_seconds())
    timestamps = _business_timestamp(n_transactions, start_ts, span_seconds, rng)

    # Amount distribution: log-normal calibrated to real retail banking
    amounts = np.round(rng.lognormal(mean=6.5, sigma=1.8, size=n_transactions), 2)
    amounts = np.clip(amounts, 1.0, 500_000.0)

    # Country lookup
    acc_index = accounts.set_index("account_id")
    src_countries = acc_index.loc[src_accounts, "country"].values
    dst_countries = acc_index.loc[dst_accounts, "country"].values

    transactions = pd.DataFrame({
        "tx_id":          [f"T{i:08d}" for i in range(n_transactions)],
        "from_account":   src_accounts,
        "to_account":     dst_accounts,
        "amount":         amounts,
        "currency":       "USD",
        "tx_type":        rng.choice(TX_TYPES, size=n_transactions, p=TX_TYPE_WEIGHTS),
        "channel":        rng.choice(CHANNELS, size=n_transactions, p=CHANNEL_WEIGHTS),
        "timestamp":      timestamps.values,
        "from_country":   src_countries,
        "to_country":     dst_countries,
        "is_cross_border": src_countries != dst_countries,
        "is_illicit":     False,
        "illicit_typology": None,
    })

    transactions = transactions.sort_values("timestamp").reset_index(drop=True)
    return transactions
