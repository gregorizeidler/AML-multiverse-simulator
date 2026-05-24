from __future__ import annotations

import numpy as np
import pandas as pd


class TimeSeriesFeatures:
    """
    Temporal and seasonal features not captured by simple rolling windows.
    These encode *when* a transaction happens, not just *how many*.
    """

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        ts = pd.to_datetime(out["timestamp"])

        # Calendar features
        out["hour_of_day"]     = ts.dt.hour
        out["day_of_week"]     = ts.dt.dayofweek        # 0=Mon, 6=Sun
        out["is_weekend"]      = (ts.dt.dayofweek >= 5).astype(int)
        out["is_night"]        = ((ts.dt.hour >= 22) | (ts.dt.hour < 6)).astype(int)
        out["month"]           = ts.dt.month
        out["quarter"]         = ts.dt.quarter

        # Cyclic encoding so ML models can learn periodicity
        out["hour_sin"]        = np.sin(2 * np.pi * out["hour_of_day"] / 24)
        out["hour_cos"]        = np.cos(2 * np.pi * out["hour_of_day"] / 24)
        out["dow_sin"]         = np.sin(2 * np.pi * out["day_of_week"] / 7)
        out["dow_cos"]         = np.cos(2 * np.pi * out["day_of_week"] / 7)
        out["month_sin"]       = np.sin(2 * np.pi * out["month"] / 12)
        out["month_cos"]       = np.cos(2 * np.pi * out["month"] / 12)

        # Account lifecycle
        out = self._account_age(out, ts)

        # Time-gap anomaly: transaction happens at unusual hour for this account
        out = self._time_anomaly(out, ts)

        return out

    def _account_age(self, df: pd.DataFrame, ts: pd.Series) -> pd.DataFrame:
        """Days since first transaction seen for each account."""
        first_seen = (
            df.groupby("from_account")["timestamp"]
            .transform("min")
        )
        first_seen = pd.to_datetime(first_seen)
        df["account_age_days"] = (ts - first_seen).dt.total_seconds() / 86400
        df["account_age_days"] = df["account_age_days"].clip(lower=0).round(1)
        return df

    def _time_anomaly(self, df: pd.DataFrame, ts: pd.Series) -> pd.DataFrame:
        """
        For each account, compute the typical hour distribution.
        Flag transactions at unusual hours (>2 std devs from mean hour).
        """
        mean_hour = df.groupby("from_account")["hour_of_day"].transform("mean")
        std_hour  = df.groupby("from_account")["hour_of_day"].transform("std").fillna(6)
        df["hour_anomaly"] = (
            np.abs(df["hour_of_day"] - mean_hour) / std_hour.clip(lower=1)
        ).round(4)
        return df
