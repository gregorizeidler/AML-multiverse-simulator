from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

CLUSTER_FEATURES = [
    "amount", "alert_score", "amount_zscore", "tx_count_1h",
    "behavioral_anomaly_score", "betweenness_centrality", "pass_through_ratio",
]


@dataclass
class Case:
    """A Case groups related alerts into a single investigative unit."""

    case_id: str
    cluster_label: int
    universe_id: str
    n_alerts: int
    total_amount: float
    avg_alert_score: float
    max_alert_score: float
    typologies: list[str]
    accounts: list[str]
    status: str = "open"
    priority: str = "medium"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    alert_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "cluster_label": self.cluster_label,
            "universe_id": self.universe_id,
            "n_alerts": self.n_alerts,
            "total_amount": self.total_amount,
            "avg_alert_score": self.avg_alert_score,
            "max_alert_score": self.max_alert_score,
            "typologies": self.typologies,
            "accounts": self.accounts,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at,
            "alert_ids": self.alert_ids[:20],
        }


class AlertClusterer:
    """
    Groups alerts into investigative cases using DBSCAN clustering on the
    alert feature space, then enriches each case with metadata.

    DBSCAN is preferred over k-means because:
      - No need to specify number of clusters
      - Handles noise (isolated alerts become singleton cases)
      - Detects clusters of arbitrary shape
    """

    def __init__(
        self,
        eps: float = 0.8,
        min_samples: int = 3,
        universe_id: str = "unknown",
    ) -> None:
        self.eps = eps
        self.min_samples = min_samples
        self.universe_id = universe_id

    def cluster(self, alerts: pd.DataFrame) -> list[Case]:
        if alerts is None or alerts.empty:
            return []

        df = alerts.copy()
        available_features = [f for f in CLUSTER_FEATURES if f in df.columns]

        if not available_features:
            return self._all_singleton(df)

        X = df[available_features].fillna(0).replace([np.inf, -np.inf], 0)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        labels = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric="euclidean",
            n_jobs=-1,
        ).fit_predict(X_scaled)

        df["_cluster"] = labels
        cases = []

        for label in sorted(df["_cluster"].unique()):
            cluster_df = df[df["_cluster"] == label]
            case = self._build_case(label, cluster_df)
            cases.append(case)

        # Sort: noise (-1) last, highest score first
        cases.sort(key=lambda c: (-c.avg_alert_score if c.cluster_label >= 0 else -999))
        return cases

    def _build_case(self, label: int, df: pd.DataFrame) -> Case:
        alert_ids = df["tx_id"].tolist() if "tx_id" in df.columns else []
        accounts = list(set(
            df["from_account"].tolist() if "from_account" in df.columns else []
        ))
        typologies = list(df["illicit_typology"].dropna().unique()) if "illicit_typology" in df.columns else []
        max_score = df["alert_score"].max() if "alert_score" in df.columns else 0.0
        avg_score = df["alert_score"].mean() if "alert_score" in df.columns else 0.0
        total_amt = df["amount"].sum() if "amount" in df.columns else 0.0

        priority = (
            "critical" if max_score >= 6.0
            else "high"   if max_score >= 4.0
            else "medium" if max_score >= 2.0
            else "low"
        )

        raw = f"{self.universe_id}-{label}-{len(df)}-{total_amt:.0f}"
        case_id = f"CASE-{hashlib.md5(raw.encode()).hexdigest()[:8].upper()}"

        return Case(
            case_id=case_id,
            cluster_label=int(label),
            universe_id=self.universe_id,
            n_alerts=len(df),
            total_amount=round(total_amt, 2),
            avg_alert_score=round(avg_score, 4),
            max_alert_score=round(max_score, 4),
            typologies=typologies,
            accounts=accounts[:10],
            priority=priority,
            status="open" if label >= 0 else "noise",
            alert_ids=alert_ids[:50],
        )

    def _all_singleton(self, df: pd.DataFrame) -> list[Case]:
        return [self._build_case(-1, df)]
