from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

# Try OpenAI, then Ollama (local), then pure heuristic
try:
    from openai import OpenAI as _OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

try:
    import httpx as _httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


@dataclass
class LLMClient:
    """
    Unified LLM client with three tiers:
      1. OpenAI API (requires OPENAI_API_KEY env var)
      2. Ollama local server (requires Ollama running on localhost:11434)
      3. Heuristic fallback (works without any external services)

    Always call .complete(system, user) → str
    """

    model: str = "gpt-4o-mini"
    ollama_model: str = "llama3"
    max_tokens: int = 1024
    temperature: float = 0.3

    _openai_client: Any = field(default=None, init=False, repr=False)
    _mode: str = field(default="heuristic", init=False)

    def __post_init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and _OPENAI_AVAILABLE:
            self._openai_client = _OpenAI(api_key=api_key)
            self._mode = "openai"
        elif self._ollama_available():
            self._mode = "ollama"
        else:
            self._mode = "heuristic"

    def _ollama_available(self) -> bool:
        if not _HTTPX_AVAILABLE:
            return False
        try:
            r = _httpx.get("http://localhost:11434/api/tags", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_real_llm(self) -> bool:
        return self._mode in ("openai", "ollama")

    def complete(self, system: str, user: str) -> str:
        if self._mode == "openai":
            return self._openai_complete(system, user)
        elif self._mode == "ollama":
            return self._ollama_complete(system, user)
        else:
            return self._heuristic_complete(system, user)

    def _openai_complete(self, system: str, user: str) -> str:
        response = self._openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content.strip()

    def _ollama_complete(self, system: str, user: str) -> str:
        import json
        prompt = f"<|system|>\n{system}\n<|user|>\n{user}\n<|assistant|>"
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        r = _httpx.post("http://localhost:11434/api/generate", json=payload, timeout=60.0)
        return r.json().get("response", "").strip()

    def _heuristic_complete(self, system: str, user: str) -> str:
        """
        Keyword-based heuristic when no LLM is available.
        Parses the user prompt and returns a structured response.
        """
        u = user.lower()

        if "sar" in u or "suspicious activity" in u:
            return self._heuristic_sar(user)
        elif "explain" in u or "why" in u or "flagged" in u:
            return self._heuristic_explain(user)
        elif "recommend" in u or "policy" in u or "best" in u:
            return self._heuristic_recommend(user)
        elif "compare" in u or "universe" in u:
            return self._heuristic_compare(user)
        else:
            return (
                "[Heuristic mode — set OPENAI_API_KEY for real LLM responses]\n\n"
                "Based on the simulation data, I can analyze AML patterns, compare universe "
                "performance, explain flagged transactions, and generate SAR narratives. "
                "Please ask a more specific question about the simulation results."
            )

    def _heuristic_sar(self, user: str) -> str:
        return (
            "[Auto-generated SAR Narrative — Heuristic Mode]\n\n"
            "Suspicious transaction activity was identified through automated monitoring. "
            "The flagged activity exhibits patterns inconsistent with the customer's established "
            "profile and known business activity. Multiple transactions were structured in a "
            "manner suggesting intentional avoidance of reporting thresholds. "
            "The pattern is consistent with layering or structuring typologies as defined under "
            "31 CFR Part 1020. A compliance officer should conduct enhanced due diligence and "
            "determine whether a SAR filing is warranted under 31 USC § 5318(g).\n\n"
            "[Set OPENAI_API_KEY for context-aware LLM narratives]"
        )

    def _heuristic_explain(self, user: str) -> str:
        factors = []
        if "amount" in user.lower():
            factors.append("the transaction amount significantly exceeds the account's historical average")
        if "velocity" in user.lower() or "count" in user.lower():
            factors.append("an unusually high number of transactions occurred within a short window")
        if "cross" in user.lower() or "border" in user.lower():
            factors.append("the transaction crossed international borders to a high-risk jurisdiction")
        if "round" in user.lower():
            factors.append("the amount is suspiciously round, a common structuring indicator")
        if not factors:
            factors = ["multiple rule thresholds were simultaneously exceeded", "the behavioral profile deviates significantly from peer-group norms"]
        return (
            f"This transaction was flagged because {'; and '.join(factors)}. "
            f"The alert score reflects the weighted sum of all triggered rules. "
            f"[Set OPENAI_API_KEY for detailed per-feature LLM explanations]"
        )

    def _heuristic_recommend(self, user: str) -> str:
        return (
            "Based on the multiverse simulation results, the recommended policy is the "
            "universe with the highest weighted ranking score (0.35×F1 + 0.30×Recall − 0.20×FPR − 0.15×cost). "
            "Consider deploying the graph-enhanced or ML-enhanced universe for production, "
            "as they combine structural and behavioral signals. Review the backtesting results "
            "to assess temporal stability before deployment. "
            "[Set OPENAI_API_KEY for LLM-powered contextual recommendations]"
        )

    def _heuristic_compare(self, user: str) -> str:
        return (
            "Universe comparison: Conservative universes maximize recall (catch more laundering) "
            "at the cost of more false positives. Aggressive universes minimize false positives "
            "but miss more illicit activity. ML-enhanced universes achieve better F1 by combining "
            "supervised signals with behavioral features. Graph-enhanced universes excel at "
            "detecting layering and round-tripping through network topology. "
            "[Set OPENAI_API_KEY for LLM-powered comparative analysis]"
        )


_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
