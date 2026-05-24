from __future__ import annotations

from typing import Any

from .client import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are an AML analyst AI assistant. Explain in plain English why a specific
transaction was flagged as suspicious by an automated AML system. Be specific, technical,
and concise (100-150 words). Reference the actual feature values provided."""


class TransactionExplainer:
    """
    Generates natural-language explanations for why a specific transaction
    was flagged (or missed) by the AML rule engine + ML model.
    """

    def __init__(self, client: LLMClient | None = None) -> None:
        self.client = client or get_llm_client()

    def explain_alert(self, transaction: dict, fired_rules: list[str], shap_values: dict | None = None) -> str:
        user = self._build_alert_prompt(transaction, fired_rules, shap_values)
        return self.client.complete(SYSTEM_PROMPT, user)

    def explain_miss(self, transaction: dict, score_gap: float, universe_name: str) -> str:
        user = f"""A transaction was NOT flagged by the '{universe_name}' AML universe even though
it was actually illicit (false negative). Explain why the system missed it and what rule changes
would have caught it.

Transaction details:
- Amount: ${transaction.get('amount', 0):,.2f}
- Alert score: {transaction.get('alert_score', 0):.3f} (threshold was {transaction.get('threshold', 0):.2f})
- Score gap: {score_gap:.3f} below threshold
- Typology: {transaction.get('illicit_typology', 'unknown')}
- Features: {self._fmt_features(transaction)}

Explain the detection failure and suggest 2-3 specific rule improvements."""
        return self.client.complete(SYSTEM_PROMPT, user)

    def _build_alert_prompt(
        self, tx: dict, fired_rules: list[str], shap: dict | None
    ) -> str:
        shap_str = ""
        if shap:
            top = sorted(shap.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            shap_str = "\nTop SHAP feature contributions:\n" + "\n".join(
                f"  {k}: {v:+.4f}" for k, v in top
            )

        return f"""Explain why this transaction was flagged as suspicious:

Transaction ID: {tx.get('tx_id', 'N/A')}
Amount: ${tx.get('amount', 0):,.2f}
Alert score: {tx.get('alert_score', 0):.3f}
Rules fired: {', '.join(fired_rules) if fired_rules else 'none'}
Is actually illicit: {tx.get('is_illicit', False)}
Illicit typology: {tx.get('illicit_typology', 'N/A')}

Key feature values:
{self._fmt_features(tx)}
{shap_str}

Write a clear, technical explanation for an AML investigator."""

    def _fmt_features(self, tx: dict) -> str:
        FEATURE_KEYS = [
            "amount_zscore", "tx_count_1h", "amount_24h", "unique_counterparties_7d",
            "behavioral_anomaly_score", "betweenness_centrality", "in_cycle",
            "pass_through_ratio", "fan_out_ratio", "xgb_score", "ensemble_score",
            "is_cross_border", "days_since_last_tx",
        ]
        lines = []
        for k in FEATURE_KEYS:
            if k in tx and tx[k] is not None:
                v = tx[k]
                lines.append(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
        return "\n".join(lines) if lines else "  (no feature data available)"
