from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .client import LLMClient, get_llm_client

SYSTEM_PROMPT = """You are an expert AML (Anti-Money Laundering) analyst AI assistant for the
AML Multiverse Simulator platform. You have access to simulation results and can answer questions
about:
- Universe performance comparison (F1, recall, precision, FPR, cost)
- Money-laundering typologies (smurfing, layering, structuring, round-tripping)
- Specific transaction alerts and why they were flagged
- Policy recommendations and threshold tuning
- SAR (Suspicious Activity Report) filing guidance
- Backtesting results and temporal drift
- Graph network analysis

Always be specific, technical, and reference actual numbers from the simulation data.
If data is not available, say so. Keep answers concise (under 200 words unless asked to elaborate)."""


class AMLChatAgent:
    """
    Conversational agent that answers questions about simulation results.
    Injects relevant simulation context into each LLM call.
    """

    def __init__(
        self,
        results_dir: str | Path,
        client: LLMClient | None = None,
        max_history: int = 10,
    ) -> None:
        self.results_dir = Path(results_dir)
        self.client = client or get_llm_client()
        self.history: list[dict[str, str]] = []
        self.max_history = max_history
        self._context: str = self._build_context()

    def _build_context(self) -> str:
        parts = []

        summary_path = self.results_dir / "simulation_summary.json"
        if summary_path.exists():
            with open(summary_path) as fh:
                summary = json.load(fh)
            dataset = summary.get("dataset", {})
            parts.append(
                f"SIMULATION DATASET: {dataset.get('n_transactions', 0):,} transactions, "
                f"{dataset.get('illicit_transactions', 0):,} illicit "
                f"({dataset.get('illicit_ratio', 0)*100:.2f}%), "
                f"{dataset.get('n_customers', 0):,} customers."
            )
            universes = summary.get("universes", [])
            parts.append(f"\nUNIVERSES ({len(universes)} total):")
            for u in universes:
                m = u.get("metrics", {})
                parts.append(
                    f"  #{u.get('rank')} {u.get('name')}: "
                    f"F1={m.get('f1', 0):.3f}, Recall={m.get('recall', 0):.3f}, "
                    f"FPR={m.get('false_positive_rate', 0):.3f}, "
                    f"Cost=${m.get('total_cost', 0):,.0f}"
                )

        rec_path = self.results_dir / "recommendations.json"
        if rec_path.exists():
            with open(rec_path) as fh:
                recs = json.load(fh)
            parts.append(f"\nBEST UNIVERSE: {recs.get('best_universe_name', 'N/A')}")
            parts.append(f"POLICY SUMMARY: {recs.get('policy_summary', '')}")

        bt_path = self.results_dir / "backtesting.json"
        if bt_path.exists():
            with open(bt_path) as fh:
                bt = json.load(fh)
            parts.append(f"\nBACKTESTING ({len(bt)} universes):")
            for r in bt:
                parts.append(
                    f"  {r.get('universe_name')}: avg_F1={r.get('avg_f1', 0):.3f}, "
                    f"drift={r.get('f1_drift', 0):+.3f}"
                )

        return "\n".join(parts) if parts else "No simulation data loaded yet."

    def chat(self, user_message: str) -> dict[str, Any]:
        self.history.append({"role": "user", "content": user_message})

        # Build full system prompt with context
        full_system = f"{SYSTEM_PROMPT}\n\n--- SIMULATION CONTEXT ---\n{self._context}"

        # Build conversation including history
        conversation = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in self.history[-self.max_history:]
        )

        response_text = self.client.complete(full_system, conversation)
        self.history.append({"role": "assistant", "content": response_text})

        return {
            "response": response_text,
            "llm_mode": self.client.mode,
            "is_real_llm": self.client.is_real_llm,
            "history_length": len(self.history),
        }

    def reset(self) -> None:
        self.history.clear()
        self._context = self._build_context()

    def refresh_context(self) -> None:
        self._context = self._build_context()
