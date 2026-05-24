from __future__ import annotations

from typing import Any


class RecommendationAgent:
    """
    Rule-based recommendation engine that analyzes all universes and produces
    actionable policy recommendations.
    """

    def generate(self, universes: list) -> dict[str, Any]:
        if not universes:
            return {"error": "No universes to analyze"}

        ranked = sorted(universes, key=lambda u: u.rank or 999)
        best = ranked[0]

        recommendations = []
        recommendations += self._recommend_from_best(best)
        recommendations += self._recommend_cross_universe(ranked)
        recommendations += self._recommend_cost_tradeoffs(ranked)

        return {
            "best_universe_id": best.universe_id,
            "best_universe_name": best.name,
            "best_metrics": best.metrics,
            "recommendations": recommendations,
            "policy_summary": self._policy_summary(best, ranked),
        }

    def _recommend_from_best(self, best) -> list[dict]:
        recs = []
        m = best.metrics

        if m.get("recall", 0) < 0.60:
            recs.append(
                {
                    "type": "threshold_adjustment",
                    "priority": "high",
                    "title": "Lower alert thresholds to improve recall",
                    "detail": (
                        f"Best universe '{best.name}' catches only "
                        f"{m.get('recall', 0)*100:.1f}% of illicit activity. "
                        "Recommend reducing alert_threshold by 20% in the YAML config."
                    ),
                    "suggested_action": f"Reduce alert_threshold from {best.config.scoring.alert_threshold} "
                                        f"to {best.config.scoring.alert_threshold * 0.8:.2f}",
                }
            )

        if m.get("false_positive_rate", 0) > 0.15:
            recs.append(
                {
                    "type": "threshold_adjustment",
                    "priority": "medium",
                    "title": "Raise thresholds on noisy rules to cut false positives",
                    "detail": (
                        f"False positive rate is {m.get('false_positive_rate', 0)*100:.1f}%. "
                        "High FPR burns investigator capacity. "
                        "Consider raising the large_transaction or cross_border rule thresholds."
                    ),
                    "suggested_action": "Increase R001 threshold by 20% or add an AND condition with velocity check",
                }
            )

        if m.get("total_cost", 0) > 1_000_000:
            recs.append(
                {
                    "type": "cost_optimization",
                    "priority": "high",
                    "title": "Total operational cost exceeds $1M",
                    "detail": (
                        f"Investigation cost: ${m.get('investigation_cost', 0):,.0f} | "
                        f"Missed laundering cost: ${m.get('missed_laundering_cost', 0):,.0f}"
                    ),
                    "suggested_action": "Prioritize reducing false negatives (missed AML) as each costs $50K vs $150 per investigation",
                }
            )

        if m.get("f1", 0) >= 0.70:
            recs.append(
                {
                    "type": "deploy_recommendation",
                    "priority": "info",
                    "title": f"Deploy '{best.name}' — strong F1 score",
                    "detail": f"F1={m.get('f1', 0):.3f}, Recall={m.get('recall', 0):.3f}, Precision={m.get('precision', 0):.3f}",
                    "suggested_action": "Proceed with deployment. Schedule monthly review against new transaction patterns.",
                }
            )

        return recs

    def _recommend_cross_universe(self, ranked: list) -> list[dict]:
        recs = []
        if len(ranked) < 2:
            return recs

        best = ranked[0]
        second = ranked[1]

        best_recall = best.metrics.get("recall", 0)
        second_precision = second.metrics.get("precision", 0)

        if (
            best_recall > second.metrics.get("recall", 0)
            and second_precision > best.metrics.get("precision", 0)
        ):
            recs.append(
                {
                    "type": "hybrid_strategy",
                    "priority": "medium",
                    "title": f"Consider hybrid of '{best.name}' and '{second.name}'",
                    "detail": (
                        f"'{best.name}' has better recall ({best_recall:.3f}) while "
                        f"'{second.name}' has better precision ({second_precision:.3f}). "
                        "A two-tier alert system could leverage both."
                    ),
                    "suggested_action": "Use graph_enhanced rules for Tier 1 (high-confidence), balanced rules for Tier 2 (medium-confidence)",
                }
            )

        return recs

    def _recommend_cost_tradeoffs(self, ranked: list) -> list[dict]:
        recs = []
        costs = [(u, u.metrics.get("total_cost", 0)) for u in ranked]
        min_cost_universe = min(costs, key=lambda x: x[1])[0]

        if min_cost_universe.universe_id != ranked[0].universe_id:
            savings = costs[0][1] - min(c for _, c in costs)
            recs.append(
                {
                    "type": "cost_analysis",
                    "priority": "low",
                    "title": f"'{min_cost_universe.name}' has lowest total cost",
                    "detail": (
                        f"Switching from best-ranked to lowest-cost universe "
                        f"saves ${savings:,.0f} but may reduce F1 by "
                        f"{(ranked[0].metrics.get('f1', 0) - min_cost_universe.metrics.get('f1', 0)):.3f}"
                    ),
                    "suggested_action": "Evaluate cost-effectiveness tradeoff based on regulatory risk appetite",
                }
            )

        return recs

    def _policy_summary(self, best, ranked: list) -> str:
        m = best.metrics
        return (
            f"Based on simulation across {len(ranked)} universe configurations, "
            f"the recommended policy is **{best.name}** (rank #{best.rank}). "
            f"It achieves F1={m.get('f1', 0):.3f} with "
            f"recall={m.get('recall', 0):.3f} and "
            f"FPR={m.get('false_positive_rate', 0):.3f}. "
            f"Estimated total operational cost: ${m.get('total_cost', 0):,.0f}/period."
        )
