from __future__ import annotations

from typing import Any

import pandas as pd


class FailureAutopsy:
    """
    Dissects false negatives (missed illicit transactions) and false positives
    (legitimate transactions wrongly flagged) per universe.
    Produces structured reports explaining *why* each failure occurred.
    """

    def analyze(self, evaluated: pd.DataFrame, config: Any) -> dict:
        false_negatives = evaluated[
            evaluated["is_illicit"] & ~evaluated["is_alerted"]
        ].copy()
        false_positives = evaluated[
            ~evaluated["is_illicit"] & evaluated["is_alerted"]
        ].copy()

        return {
            "false_negatives": self._analyze_fn(false_negatives, config),
            "false_positives": self._analyze_fp(false_positives, config),
            "fn_by_typology": self._fn_by_typology(false_negatives),
            "fn_summary": self._fn_summary(false_negatives, evaluated),
            "fp_summary": self._fp_summary(false_positives, evaluated),
        }

    def _analyze_fn(self, fn_df: pd.DataFrame, config: Any) -> list[dict]:
        results = []
        for _, row in fn_df.head(50).iterrows():
            fired_rules = [
                col.replace("rule_", "").replace("_hit", "")
                for col in fn_df.columns
                if col.startswith("rule_") and col.endswith("_hit") and row.get(col, False)
            ]
            missed_rules = [
                rule.id
                for rule in config.rules
                if rule.id not in fired_rules
            ]
            results.append(
                {
                    "tx_id": row.get("tx_id", ""),
                    "typology": row.get("illicit_typology", "unknown"),
                    "amount": row.get("amount", 0),
                    "alert_score": row.get("alert_score", 0),
                    "threshold": config.scoring.alert_threshold,
                    "score_gap": round(
                        config.scoring.alert_threshold - row.get("alert_score", 0), 4
                    ),
                    "rules_fired": fired_rules,
                    "rules_missed": missed_rules,
                    "reason": self._explain_miss(row, config),
                }
            )
        return results

    def _analyze_fp(self, fp_df: pd.DataFrame, config: Any) -> list[dict]:
        results = []
        for _, row in fp_df.head(50).iterrows():
            fired_rules = [
                col.replace("rule_", "").replace("_hit", "")
                for col in fp_df.columns
                if col.startswith("rule_") and col.endswith("_hit") and row.get(col, False)
            ]
            results.append(
                {
                    "tx_id": row.get("tx_id", ""),
                    "amount": row.get("amount", 0),
                    "alert_score": row.get("alert_score", 0),
                    "rules_fired": fired_rules,
                    "reason": self._explain_fp(row, fired_rules),
                }
            )
        return results

    def _fn_by_typology(self, fn_df: pd.DataFrame) -> dict[str, int]:
        if fn_df.empty or "illicit_typology" not in fn_df.columns:
            return {}
        return fn_df["illicit_typology"].value_counts().to_dict()

    def _fn_summary(self, fn_df: pd.DataFrame, all_df: pd.DataFrame) -> dict:
        total_illicit = int(all_df["is_illicit"].sum())
        return {
            "total_missed": len(fn_df),
            "total_illicit": total_illicit,
            "miss_rate": round(len(fn_df) / max(total_illicit, 1), 4),
            "avg_amount_missed": round(fn_df["amount"].mean(), 2) if not fn_df.empty else 0,
            "avg_score_gap": round(
                fn_df["alert_score"].mean(), 4
            ) if "alert_score" in fn_df.columns and not fn_df.empty else 0,
        }

    def _fp_summary(self, fp_df: pd.DataFrame, all_df: pd.DataFrame) -> dict:
        total_legit = int((~all_df["is_illicit"]).sum())
        return {
            "total_false_alerts": len(fp_df),
            "total_legitimate": total_legit,
            "fp_rate": round(len(fp_df) / max(total_legit, 1), 4),
            "avg_amount_fp": round(fp_df["amount"].mean(), 2) if not fp_df.empty else 0,
        }

    def _explain_miss(self, row: pd.Series, config: Any) -> str:
        score = row.get("alert_score", 0)
        threshold = config.scoring.alert_threshold
        gap = threshold - score
        if gap <= 0.5:
            return f"Score {score:.2f} just below threshold {threshold:.2f} — minor threshold relaxation would capture"
        elif score == 0:
            return "No rules fired — transaction features are below all rule thresholds"
        else:
            return f"Score {score:.2f} significantly below threshold {threshold:.2f} — requires new rules or lower thresholds"

    def _explain_fp(self, row: pd.Series, fired_rules: list[str]) -> str:
        if not fired_rules:
            return "Alert triggered but no individual rules recorded"
        n = len(fired_rules)
        return f"{n} rule(s) fired ({', '.join(fired_rules[:3])}) on legitimate transaction — consider raising thresholds or adding AND conditions"
