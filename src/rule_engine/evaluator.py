from __future__ import annotations

import operator as op
from typing import Callable

import numpy as np
import pandas as pd

from .loader import RuleConfig, UniverseConfig

OPERATORS: dict[str, Callable] = {
    ">": op.gt,
    ">=": op.ge,
    "<": op.lt,
    "<=": op.le,
    "==": op.eq,
    "!=": op.ne,
}


class RuleEvaluator:
    """
    Applies all rules in a UniverseConfig to a feature-enriched transaction
    DataFrame and produces per-transaction alert scores.
    """

    def __init__(self, config: UniverseConfig) -> None:
        self.config = config

    def evaluate(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Parameters
        ----------
        features : DataFrame with one row per transaction; must contain
                   columns referenced by rule fields.

        Returns
        -------
        DataFrame with added columns:
            - rule_<rule_id>_hit  : bool — whether the rule fired
            - alert_score         : float — weighted sum of fired rules
            - is_alerted          : bool — score >= alert_threshold
            - is_high_risk        : bool — score >= high_risk_threshold
        """
        df = features.copy()
        score = np.zeros(len(df), dtype=float)

        for rule in self.config.rules:
            hit_col = f"rule_{rule.id}_hit"
            df[hit_col] = self._apply_rule(df, rule)
            score += df[hit_col].astype(float) * rule.weight

        df["alert_score"] = np.round(score, 4)
        df["is_alerted"] = df["alert_score"] >= self.config.scoring.alert_threshold
        df["is_high_risk"] = df["alert_score"] >= self.config.scoring.high_risk_threshold
        return df

    def _apply_rule(self, df: pd.DataFrame, rule: RuleConfig) -> pd.Series:
        if rule.field not in df.columns:
            return pd.Series(False, index=df.index)

        cmp_fn = OPERATORS.get(rule.operator)
        if cmp_fn is None:
            raise ValueError(f"Unknown operator '{rule.operator}' in rule {rule.id}")

        col = pd.to_numeric(df[rule.field], errors="coerce").fillna(0)
        return cmp_fn(col, rule.threshold)
