from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


class BehavioralFeatures:
    """
    Computes behavioral anomaly scores based on each account's own historical
    patterns and peer-group comparisons.
    """

    def transform(
        self, transactions: pd.DataFrame, accounts: pd.DataFrame
    ) -> pd.DataFrame:
        df = transactions.copy()
        df = self._peer_group_deviation(df, accounts)
        df = self._behavioral_anomaly_score(df)
        return df

    def _peer_group_deviation(
        self, df: pd.DataFrame, accounts: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compares each transaction amount to the mean of transactions from
        accounts in the same risk_level bucket (peer group).
        """
        acc_risk = accounts[["account_id", "risk_level"]].rename(
            columns={"account_id": "from_account"}
        )
        df = df.merge(acc_risk, on="from_account", how="left")
        df["risk_level"] = df["risk_level"].fillna("low")

        peer_stats = (
            df.groupby("risk_level")["amount"]
            .agg(peer_mean="mean", peer_std="std")
            .reset_index()
        )
        peer_stats["peer_std"] = peer_stats["peer_std"].fillna(1).replace(0, 1)
        df = df.merge(peer_stats, on="risk_level", how="left")

        df["peer_group_deviation"] = (
            (df["amount"] - df["peer_mean"]) / df["peer_std"]
        ).round(4)
        df = df.drop(columns=["peer_mean", "peer_std", "risk_level"])
        return df

    def _behavioral_anomaly_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Composite score combining z-score, peer deviation, velocity, and
        cross-border flags into a [0, 1] anomaly score.
        """
        features = ["amount_zscore", "peer_group_deviation", "tx_count_24h", "is_cross_border"]
        available = [f for f in features if f in df.columns]

        if not available:
            df["behavioral_anomaly_score"] = 0.0
            return df

        X = df[available].fillna(0).copy()
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        raw_score = np.abs(X_scaled).mean(axis=1)
        # Sigmoid normalization to [0, 1]
        df["behavioral_anomaly_score"] = np.round(
            1 / (1 + np.exp(-raw_score + 1)), 4
        )
        return df
