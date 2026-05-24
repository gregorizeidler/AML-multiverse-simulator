from __future__ import annotations

import pandas as pd

from .loader import UniverseConfig


class AlertManager:
    """
    Aggregates rule evaluation results into structured alerts.
    Each alert references the transaction(s) that triggered it,
    the rules that fired, and the risk score.
    """

    def __init__(self, config: UniverseConfig) -> None:
        self.config = config

    def build_alerts(self, evaluated: pd.DataFrame) -> pd.DataFrame:
        """
        Parameters
        ----------
        evaluated : output of RuleEvaluator.evaluate()

        Returns
        -------
        DataFrame of alerts — one row per alerted transaction.
        """
        alerted = evaluated[evaluated["is_alerted"]].copy()
        if alerted.empty:
            return pd.DataFrame()

        rule_cols = [c for c in alerted.columns if c.startswith("rule_") and c.endswith("_hit")]
        rule_ids = [c.replace("rule_", "").replace("_hit", "") for c in rule_cols]

        def _fired_rules(row: pd.Series) -> list[str]:
            return [
                rule_id
                for rule_id, col in zip(rule_ids, rule_cols)
                if row.get(col, False)
            ]

        alerted["fired_rules"] = alerted.apply(_fired_rules, axis=1)
        alerted["n_rules_fired"] = alerted["fired_rules"].apply(len)
        alerted["alert_level"] = alerted["alert_score"].apply(self._classify_level)

        cols = [
            "tx_id",
            "from_account",
            "to_account",
            "amount",
            "timestamp",
            "alert_score",
            "alert_level",
            "fired_rules",
            "n_rules_fired",
            "is_illicit",
            "illicit_typology",
        ]
        present = [c for c in cols if c in alerted.columns]
        return alerted[present].reset_index(drop=True)

    def _classify_level(self, score: float) -> str:
        if score >= self.config.scoring.high_risk_threshold:
            return "critical"
        elif score >= self.config.scoring.alert_threshold * 1.5:
            return "high"
        elif score >= self.config.scoring.alert_threshold:
            return "medium"
        return "low"
