from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class WindowResult:
    window_id: int
    window_start: str
    window_end: str
    n_transactions: int
    n_illicit: int
    n_alerts: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    total_cost: float
    universe_id: str
    f1_ci: tuple[float, float] = (0.0, 0.0)  # 95% bootstrap CI

    def to_dict(self) -> dict:
        return {
            "window_id": self.window_id,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "n_transactions": self.n_transactions,
            "n_illicit": self.n_illicit,
            "n_alerts": self.n_alerts,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "f1_ci_lo": self.f1_ci[0],
            "f1_ci_hi": self.f1_ci[1],
            "false_positive_rate": self.false_positive_rate,
            "total_cost": self.total_cost,
            "universe_id": self.universe_id,
        }


@dataclass
class BacktestResults:
    universe_id: str
    universe_name: str
    window_size_days: int
    windows: list[WindowResult]
    mannwhitney_tests: list[dict] = field(default_factory=list)

    @property
    def avg_f1(self) -> float:
        if not self.windows:
            return 0.0
        return float(np.mean([w.f1 for w in self.windows]))

    @property
    def f1_drift(self) -> float:
        if len(self.windows) < 2:
            return 0.0
        return self.windows[-1].f1 - self.windows[0].f1

    @property
    def f1_std(self) -> float:
        if not self.windows:
            return 0.0
        return float(np.std([w.f1 for w in self.windows]))

    @property
    def n_significant_changes(self) -> int:
        return sum(1 for t in self.mannwhitney_tests if t.get("significant"))

    def to_dict(self) -> dict:
        return {
            "universe_id":   self.universe_id,
            "universe_name": self.universe_name,
            "window_size_days": self.window_size_days,
            "avg_f1":        round(self.avg_f1, 4),
            "f1_drift":      round(self.f1_drift, 4),
            "f1_std":        round(self.f1_std, 4),
            "n_significant_changes": self.n_significant_changes,
            "windows":       [w.to_dict() for w in self.windows],
            "mannwhitney_tests": self.mannwhitney_tests,
        }
