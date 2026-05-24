from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SARSubject:
    account_id: str
    role: str  # "originator" | "intermediary" | "beneficiary"
    transaction_count: int
    total_amount: float
    countries: list[str]


@dataclass
class SARReport:
    """
    Structured Suspicious Activity Report (SAR) — aligned with FinCEN format.
    """

    sar_id: str
    universe_id: str
    filing_date: str
    activity_start: str
    activity_end: str
    primary_typology: str
    typologies_detected: list[str]

    subjects: list[SARSubject]
    transactions: list[dict]

    total_suspicious_amount: float
    n_transactions: int
    avg_alert_score: float
    max_alert_score: float

    narrative: str
    recommended_actions: list[str]

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sar_id": self.sar_id,
            "universe_id": self.universe_id,
            "filing_date": self.filing_date,
            "activity_period": {
                "start": self.activity_start,
                "end": self.activity_end,
            },
            "typologies": {
                "primary": self.primary_typology,
                "all_detected": self.typologies_detected,
            },
            "subjects": [
                {
                    "account_id": s.account_id,
                    "role": s.role,
                    "transaction_count": s.transaction_count,
                    "total_amount": s.total_amount,
                    "countries": s.countries,
                }
                for s in self.subjects
            ],
            "financial_activity": {
                "total_suspicious_amount": self.total_suspicious_amount,
                "n_transactions": self.n_transactions,
                "avg_alert_score": self.avg_alert_score,
                "max_alert_score": self.max_alert_score,
            },
            "narrative": self.narrative,
            "recommended_actions": self.recommended_actions,
            "metadata": self.metadata,
            "sample_transactions": self.transactions[:10],
        }
