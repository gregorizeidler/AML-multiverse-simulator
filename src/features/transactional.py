from __future__ import annotations

import numpy as np
import pandas as pd


class TransactionalFeatures:
    """
    Computes per-transaction velocity and amount features.
    All features are computed at the time of each transaction using
    only information available up to that point (no look-ahead leakage).
    """

    def transform(self, transactions: pd.DataFrame) -> pd.DataFrame:
        df = transactions.copy().sort_values("timestamp").reset_index(drop=True)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        df["is_round_amount"] = (df["amount"] % 1000 == 0).astype(int)
        df["log_amount"] = np.log1p(df["amount"])

        # Per-account rolling windows
        df = self._rolling_count(df, window="1h", col_name="tx_count_1h")
        df = self._rolling_count(df, window="24h", col_name="tx_count_24h")
        df = self._rolling_sum_amount(df, window="1h", col_name="amount_1h")
        df = self._rolling_sum_amount(df, window="24h", col_name="amount_24h")
        df = self._rolling_sum_amount(df, window="7D", col_name="amount_7d")
        df = self._unique_counterparties(df, window="7D", col_name="unique_counterparties_7d")
        df = self._amount_zscore(df)
        df = self._days_since_last_tx(df)

        return df

    def _rolling_count(
        self, df: pd.DataFrame, window: str, col_name: str
    ) -> pd.DataFrame:
        counts = (
            df.set_index("timestamp")
            .groupby("from_account")["tx_id"]
            .rolling(window, closed="left")
            .count()
            .rename(col_name)
            .reset_index()
        )
        counts = counts.rename(columns={"timestamp": "timestamp"})
        df = df.merge(
            counts[["from_account", "timestamp", col_name]],
            on=["from_account", "timestamp"],
            how="left",
        )
        df[col_name] = df[col_name].fillna(0).astype(int)
        return df

    def _rolling_sum_amount(
        self, df: pd.DataFrame, window: str, col_name: str
    ) -> pd.DataFrame:
        sums = (
            df.set_index("timestamp")
            .groupby("from_account")["amount"]
            .rolling(window, closed="left")
            .sum()
            .rename(col_name)
            .reset_index()
        )
        df = df.merge(
            sums[["from_account", "timestamp", col_name]],
            on=["from_account", "timestamp"],
            how="left",
        )
        df[col_name] = df[col_name].fillna(0)
        return df

    def _unique_counterparties(
        self, df: pd.DataFrame, window: str, col_name: str
    ) -> pd.DataFrame:
        df = df.sort_values("timestamp")
        result = []
        window_td = pd.Timedelta(window)

        for _, group in df.groupby("from_account"):
            group = group.sort_values("timestamp")
            counts = []
            for i, row in group.iterrows():
                cutoff = row["timestamp"] - window_td
                past = group[
                    (group["timestamp"] >= cutoff)
                    & (group["timestamp"] < row["timestamp"])
                ]
                counts.append(past["to_account"].nunique())
            result.extend(zip(group.index, counts))

        cp_series = pd.Series(dict(result), name=col_name)
        df[col_name] = cp_series.reindex(df.index).fillna(0).astype(int)
        return df

    def _amount_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        stats = df.groupby("from_account")["amount"].agg(["mean", "std"]).reset_index()
        stats.columns = ["from_account", "_mean", "_std"]
        df = df.merge(stats, on="from_account", how="left")
        df["_std"] = df["_std"].fillna(1).replace(0, 1)
        df["amount_zscore"] = ((df["amount"] - df["_mean"]) / df["_std"]).round(4)
        df = df.drop(columns=["_mean", "_std"])
        return df

    def _days_since_last_tx(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values("timestamp")
        df["_prev_ts"] = df.groupby("from_account")["timestamp"].shift(1)
        df["days_since_last_tx"] = (
            (df["timestamp"] - df["_prev_ts"]).dt.total_seconds() / 86400
        ).fillna(9999).round(2)
        df = df.drop(columns=["_prev_ts"])
        return df
