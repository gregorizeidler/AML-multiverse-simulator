from __future__ import annotations

"""
RAG-enhanced AML Chat Agent.

Retrieval-Augmented Generation: before calling the LLM, we retrieve
the top-K most relevant alert/transaction records using TF-IDF cosine
similarity on their textual representation.

This allows the LLM to answer questions like:
  "Show me the 3 highest-scoring smurfing alerts"
  "Which accounts have the highest gnn_score?"
  "What are the flagged TBML transactions?"

without hallucinating — the answer is grounded in actual data.

Architecture:
  1. Index build: convert alerts/transactions to text snippets → TF-IDF matrix
  2. Query: user question → TF-IDF vector → cosine similarity → top-K snippets
  3. Augment: inject retrieved snippets as context into LLM prompt
  4. Generate: LLM produces grounded answer
"""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .client import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are an expert AML analyst AI with access to real simulation data.
You answer questions about specific alerts, transactions, and accounts using the retrieved
context provided. Be specific, cite actual values from the context, and be concise (under 200 words).
If the retrieved context doesn't contain the answer, say so clearly."""


class RAGIndex:
    """
    TF-IDF index over alert and transaction records.
    Each record is converted to a natural-language snippet for indexing.
    """

    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._records: list[dict] = []

    def build(self, records: list[dict], text_fn=None) -> "RAGIndex":
        if not records:
            return self
        self._records = records
        texts = [text_fn(r) if text_fn else self._default_text(r) for r in records]
        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
        )
        self._matrix = self._vectorizer.fit_transform(texts)
        return self

    def query(self, q: str, top_k: int = 5) -> list[dict]:
        if self._vectorizer is None or self._matrix is None:
            return []
        q_vec = self._vectorizer.transform([q])
        sims = cosine_similarity(q_vec, self._matrix).flatten()
        top_indices = sims.argsort()[::-1][:top_k]
        return [
            {**self._records[i], "_similarity": round(float(sims[i]), 4)}
            for i in top_indices
            if sims[i] > 0.01
        ]

    @staticmethod
    def _default_text(record: dict) -> str:
        parts = []
        for k, v in record.items():
            if v is not None and v != "" and k not in ("_similarity",):
                parts.append(f"{k.replace('_', ' ')}: {v}")
        return " | ".join(parts)


class RAGChatAgent:
    """
    AML Chat Agent with Retrieval-Augmented Generation.
    Indexes alerts, transactions, and SAR reports for grounded Q&A.
    """

    def __init__(
        self,
        results_dir: str | Path,
        client: LLMClient | None = None,
        max_history: int = 8,
        top_k_retrieve: int = 5,
    ) -> None:
        self.results_dir = Path(results_dir)
        self.client = client or get_llm_client()
        self.max_history = max_history
        self.top_k = top_k_retrieve
        self.history: list[dict] = []

        self._summary_context = self._load_summary()
        self._alert_index = RAGIndex()
        self._sar_index = RAGIndex()
        self._universe_index = RAGIndex()
        self._build_indexes()

    def _load_summary(self) -> str:
        path = self.results_dir / "simulation_summary.json"
        if not path.exists():
            return "No simulation data loaded."
        try:
            with open(path) as fh:
                summary = json.load(fh)
            dataset = summary.get("dataset", {})
            universes = summary.get("universes", [])
            lines = [
                f"Dataset: {dataset.get('n_transactions', 0):,} transactions, "
                f"{dataset.get('illicit_transactions', 0):,} illicit ({dataset.get('illicit_ratio', 0)*100:.2f}%).",
                f"{len(universes)} universes simulated:",
            ]
            for u in universes:
                m = u.get("metrics", {})
                lines.append(
                    f"  #{u.get('rank')} {u.get('name')}: "
                    f"F1={m.get('f1', 0):.3f} Recall={m.get('recall', 0):.3f} "
                    f"FPR={m.get('false_positive_rate', 0):.3f} Cost=${m.get('total_cost', 0):,.0f}"
                )
            return "\n".join(lines)
        except Exception:
            return "Summary unavailable."

    def _build_indexes(self) -> None:
        # Index alerts from best universe
        alert_records = []
        for p in sorted(self.results_dir.glob("*_alerts.parquet")):
            try:
                df = pd.read_parquet(p).head(2000)
                alert_records.extend(df.fillna("").to_dict(orient="records"))
            except Exception:
                pass

        if alert_records:
            self._alert_index.build(
                alert_records,
                text_fn=lambda r: (
                    f"alert tx_id {r.get('tx_id', '')} "
                    f"from account {r.get('from_account', '')} "
                    f"amount ${r.get('amount', 0):,.2f} "
                    f"score {r.get('alert_score', 0)} "
                    f"typology {r.get('illicit_typology', 'unknown')} "
                    f"level {r.get('alert_level', '')} "
                    f"rules {r.get('fired_rules', '')}"
                ),
            )

        # Index SAR reports
        sar_path = self.results_dir / "sar_reports.json"
        if sar_path.exists():
            try:
                with open(sar_path) as fh:
                    sars = json.load(fh)
                self._sar_index.build(
                    sars,
                    text_fn=lambda r: (
                        f"SAR {r.get('sar_id', '')} "
                        f"typology {r.get('typology', '')} "
                        f"amount ${r.get('total_amount', 0):,.2f} "
                        f"transactions {r.get('n_transactions', 0)} "
                        f"narrative {r.get('narrative', '')[:200]}"
                    ),
                )
            except Exception:
                pass

    def chat(self, user_message: str) -> dict[str, Any]:
        # Retrieve relevant records
        alert_hits = self._alert_index.query(user_message, top_k=self.top_k)
        sar_hits   = self._sar_index.query(user_message, top_k=3)

        retrieved_context = self._format_retrieved(alert_hits, sar_hits)

        self.history.append({"role": "user", "content": user_message})

        full_system = (
            f"{SYSTEM_PROMPT}\n\n"
            f"=== SIMULATION OVERVIEW ===\n{self._summary_context}\n\n"
            f"=== RETRIEVED CONTEXT (most relevant records) ===\n{retrieved_context}"
        )

        conversation = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in self.history[-self.max_history:]
        )

        response = self.client.complete(full_system, conversation)
        self.history.append({"role": "assistant", "content": response})

        return {
            "response": response,
            "llm_mode": self.client.mode,
            "is_real_llm": self.client.is_real_llm,
            "retrieved_alerts": len(alert_hits),
            "retrieved_sars": len(sar_hits),
            "history_length": len(self.history),
            "top_alert_ids": [r.get("tx_id") for r in alert_hits[:3] if r.get("tx_id")],
        }

    def _format_retrieved(self, alerts: list[dict], sars: list[dict]) -> str:
        parts = []
        if alerts:
            parts.append("Relevant Alerts:")
            for i, a in enumerate(alerts, 1):
                parts.append(
                    f"  {i}. TX {a.get('tx_id')} | "
                    f"From: {a.get('from_account')} | "
                    f"Amount: ${a.get('amount', 0):,.2f} | "
                    f"Score: {a.get('alert_score', 0)} | "
                    f"Typology: {a.get('illicit_typology', 'N/A')} | "
                    f"Level: {a.get('alert_level', 'N/A')}"
                )
        if sars:
            parts.append("Relevant SARs:")
            for i, s in enumerate(sars, 1):
                parts.append(
                    f"  {i}. SAR {s.get('sar_id')} | "
                    f"Typology: {s.get('typology')} | "
                    f"Amount: ${s.get('total_amount', 0):,.2f} | "
                    f"Transactions: {s.get('n_transactions')}"
                )
        return "\n".join(parts) if parts else "No relevant records found."

    def reset(self) -> None:
        self.history.clear()
        self._summary_context = self._load_summary()
        self._build_indexes()
