from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..rule_engine.loader import UniverseConfig


@dataclass
class Universe:
    """
    Encapsulates a single parallel universe: its configuration, the evaluated
    transactions, generated alerts, computed metrics, and ranking score.
    """

    config: UniverseConfig
    features: pd.DataFrame | None = field(default=None, repr=False)
    alerts: pd.DataFrame | None = field(default=None, repr=False)
    metrics: dict[str, Any] = field(default_factory=dict)
    rank: int | None = None
    graph_summary: dict = field(default_factory=dict)

    @property
    def universe_id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    def to_summary_dict(self) -> dict:
        return {
            "universe_id": self.universe_id,
            "name": self.name,
            "rank": self.rank,
            "metrics": self.metrics,
            "graph_summary": self.graph_summary,
            "n_alerts": len(self.alerts) if self.alerts is not None else 0,
            "n_rules": len(self.config.rules),
            "alert_threshold": self.config.scoring.alert_threshold,
            "high_risk_threshold": self.config.scoring.high_risk_threshold,
        }
