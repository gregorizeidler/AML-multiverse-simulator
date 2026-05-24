from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .report import SARReport, SARSubject

TYPOLOGY_NARRATIVES = {
    "smurfing": (
        "Multiple transactions were observed originating from different accounts "
        "and converging on a single destination account within a compressed time window. "
        "Each individual transaction was structured to fall below the $10,000 Currency "
        "Transaction Reporting (CTR) threshold, a pattern consistent with smurfing. "
        "The coordinated nature and timing of these transactions suggest deliberate "
        "avoidance of regulatory reporting obligations."
    ),
    "layering": (
        "Funds were observed moving through a sequential chain of accounts in rapid "
        "succession, with each transfer slightly reducing the amount — consistent with "
        "fee skimming during layering. This multi-hop structure is designed to obscure "
        "the original source of funds and create a complex audit trail. The pattern "
        "is indicative of the layering phase of money laundering."
    ),
    "structuring": (
        "A single account made repeated deposits or withdrawals systematically below "
        "the $10,000 CTR threshold over an extended period. The consistency and "
        "regularity of the sub-threshold amounts — combined with the absence of a "
        "legitimate business explanation — indicates deliberate structuring to avoid "
        "mandatory currency transaction reporting."
    ),
    "round_tripping": (
        "Funds were traced leaving the originating account, transiting through one or "
        "more foreign jurisdictions classified as high-risk by FATF, and returning "
        "to the originating account or a closely associated account. This circular "
        "flow, commonly called round-tripping, is used to disguise illicit funds as "
        "legitimate foreign investment income."
    ),
}

RECOMMENDED_ACTIONS = {
    "smurfing": [
        "File CTR for aggregate transactions exceeding $10,000 by the same beneficial owner",
        "Freeze implicated accounts pending AML investigation",
        "Request source-of-funds documentation from account holders",
        "Escalate to law enforcement if structuring is confirmed",
    ],
    "layering": [
        "Map the full transaction chain and identify the ultimate beneficial owner",
        "Issue account holds on all intermediary accounts",
        "Request correspondent bank records for cross-border legs",
        "Submit SAR to FinCEN within 30 days of detection",
    ],
    "structuring": [
        "File SAR for structuring under 31 USC § 5324",
        "Review 90-day lookback for similar patterns",
        "Contact branch operations for in-person transaction records",
        "Consider Suspicious Activity Report to IRS for tax evasion indicators",
    ],
    "round_tripping": [
        "Conduct enhanced due diligence on all foreign counterparties",
        "Request SWIFT MT103 records for cross-border transfers",
        "Assess PEP (Politically Exposed Person) connections",
        "Coordinate with OFAC for sanctions screening",
    ],
}


class SARGenerator:
    """
    Groups high-risk alerts by account cluster and typology, then generates
    structured SAR reports for each group.
    """

    def __init__(self, universe_id: str, min_cluster_size: int = 3) -> None:
        self.universe_id = universe_id
        self.min_cluster_size = min_cluster_size

    def generate_all(
        self,
        alerts: pd.DataFrame,
        evaluated: pd.DataFrame,
    ) -> list[SARReport]:
        """
        Generate one SAR per typology found in high-risk alerts.
        """
        if alerts is None or alerts.empty:
            return []

        # Only process high-confidence alerts
        high_risk = alerts[alerts["alert_level"].isin(["critical", "high"])].copy()
        if high_risk.empty:
            return []

        # Merge with full evaluated df to get all features
        high_risk = high_risk.merge(
            evaluated[["tx_id", "is_illicit", "illicit_typology"]].drop_duplicates("tx_id"),
            on="tx_id",
            how="left",
            suffixes=("", "_eval"),
        )

        reports = []
        for typology in high_risk["illicit_typology"].dropna().unique():
            group = high_risk[high_risk["illicit_typology"] == typology]
            if len(group) < self.min_cluster_size:
                continue
            report = self._build_report(typology, group, evaluated)
            reports.append(report)

        # Also generate one "mixed" report for unclassified high-risk alerts
        unclassified = high_risk[high_risk["illicit_typology"].isna()]
        if len(unclassified) >= self.min_cluster_size:
            reports.append(self._build_report("unknown", unclassified, evaluated))

        return reports

    def _build_report(
        self,
        typology: str,
        group: pd.DataFrame,
        evaluated: pd.DataFrame,
    ) -> SARReport:
        sar_id = self._make_sar_id(typology, group)

        # Timeline
        timestamps = pd.to_datetime(group["timestamp"], errors="coerce")
        activity_start = str(timestamps.min().date()) if not timestamps.isna().all() else "unknown"
        activity_end = str(timestamps.max().date()) if not timestamps.isna().all() else "unknown"

        # Subjects
        subjects = self._extract_subjects(group, evaluated)

        # All typologies in the report scope
        all_typologies = group["illicit_typology"].dropna().unique().tolist()
        if "unknown" not in all_typologies and typology == "unknown":
            all_typologies = ["mixed"]

        transactions = group[
            ["tx_id", "from_account", "to_account", "amount", "timestamp", "alert_score"]
        ].to_dict(orient="records") if all(
            c in group.columns for c in ["tx_id", "from_account", "to_account"]
        ) else []

        narrative = self._compose_narrative(typology, subjects, group)
        recommended = RECOMMENDED_ACTIONS.get(typology, [
            "Conduct enhanced due diligence",
            "File SAR with FinCEN",
            "Escalate to compliance officer",
        ])

        return SARReport(
            sar_id=sar_id,
            universe_id=self.universe_id,
            filing_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            activity_start=activity_start,
            activity_end=activity_end,
            primary_typology=typology,
            typologies_detected=list(set(all_typologies)),
            subjects=subjects,
            transactions=transactions,
            total_suspicious_amount=round(group["amount"].sum(), 2),
            n_transactions=len(group),
            avg_alert_score=round(group["alert_score"].mean(), 4),
            max_alert_score=round(group["alert_score"].max(), 4),
            narrative=narrative,
            recommended_actions=recommended,
            metadata={
                "generator": "AMLMultiverseSimulator",
                "universe": self.universe_id,
                "typology_cluster_size": len(group),
            },
        )

    def _extract_subjects(
        self, group: pd.DataFrame, evaluated: pd.DataFrame
    ) -> list[SARSubject]:
        subjects = []
        if "from_account" not in group.columns:
            return subjects

        all_accounts = set(group["from_account"].tolist())
        if "to_account" in group.columns:
            all_accounts |= set(group["to_account"].tolist())

        for acct in list(all_accounts)[:10]:
            as_sender = group[group.get("from_account", pd.Series()) == acct] if "from_account" in group.columns else pd.DataFrame()
            as_receiver = group[group.get("to_account", pd.Series()) == acct] if "to_account" in group.columns else pd.DataFrame()

            n_tx = len(as_sender) + len(as_receiver)
            total_amt = as_sender["amount"].sum() if not as_sender.empty else 0.0

            countries = []
            if "from_country" in group.columns and not as_sender.empty:
                countries += as_sender["from_country"].dropna().unique().tolist()

            role = (
                "originator" if len(as_sender) > len(as_receiver)
                else "beneficiary" if len(as_receiver) > len(as_sender)
                else "intermediary"
            )

            subjects.append(
                SARSubject(
                    account_id=str(acct),
                    role=role,
                    transaction_count=n_tx,
                    total_amount=round(total_amt, 2),
                    countries=list(set(countries))[:5],
                )
            )
        return subjects

    def _compose_narrative(
        self,
        typology: str,
        subjects: list[SARSubject],
        group: pd.DataFrame,
    ) -> str:
        base = TYPOLOGY_NARRATIVES.get(
            typology,
            "Suspicious transaction patterns were detected that do not conform to "
            "the customer's expected behavior or business profile.",
        )
        total_amt = group["amount"].sum()
        n_tx = len(group)
        n_subjects = len(subjects)
        acct_list = ", ".join(s.account_id for s in subjects[:3])

        return (
            f"[AUTOMATED SAR NARRATIVE — REVIEW BEFORE FILING]\n\n"
            f"{base}\n\n"
            f"This report covers {n_tx} transaction(s) totaling ${total_amt:,.2f} USD "
            f"involving {n_subjects} account(s) ({acct_list}{', and others' if n_subjects > 3 else ''}). "
            f"The activity was flagged by the AML Multiverse Simulator under universe "
            f"'{self.universe_id}' with an average alert score of {group['alert_score'].mean():.2f}. "
            f"\n\nThis narrative was auto-generated. A compliance officer must review, "
            f"validate, and complete this SAR before submission to FinCEN."
        )

    @staticmethod
    def _make_sar_id(typology: str, group: pd.DataFrame) -> str:
        raw = f"{typology}-{len(group)}-{group['amount'].sum():.0f}"
        h = hashlib.md5(raw.encode()).hexdigest()[:8].upper()
        return f"SAR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{h}"
