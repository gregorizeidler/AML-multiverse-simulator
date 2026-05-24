from __future__ import annotations

import numpy as np


class UniverseRanker:
    """
    Multi-criteria ranking with:
      1. Primary: weighted linear score (w_f1, w_recall, w_fpr, w_cost)
      2. Pareto frontier: non-dominated sorting on (F1, Cost)
         — universes on the frontier are never dominated by another
           on ALL criteria simultaneously
      3. Sensitivity analysis: how much does rank change if weights shift?
    """

    def __init__(
        self,
        w_f1: float = 0.35,
        w_recall: float = 0.30,
        w_fpr: float = 0.20,
        w_cost: float = 0.15,
    ) -> None:
        self.w_f1 = w_f1
        self.w_recall = w_recall
        self.w_fpr = w_fpr
        self.w_cost = w_cost

    def rank(self, universes: list) -> list:
        if not universes:
            return []

        metrics_list = [u.metrics for u in universes]
        costs = np.array([m.get("total_cost", 0) for m in metrics_list], dtype=float)
        cost_max = costs.max() if costs.max() > 0 else 1.0
        costs_norm = costs / cost_max

        scores = []
        for m, cost_norm in zip(metrics_list, costs_norm):
            score = (
                self.w_f1     * m.get("f1", 0)
                + self.w_recall * m.get("recall", 0)
                - self.w_fpr    * m.get("false_positive_rate", 0)
                - self.w_cost   * cost_norm
            )
            scores.append(score)

        ranked = sorted(
            zip(universes, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        # Pareto frontier
        pareto_ids = self._pareto_frontier(universes)

        # Sensitivity analysis
        sensitivity = self._sensitivity(universes, costs_norm)

        for rank_idx, (universe, score) in enumerate(ranked, start=1):
            universe.rank = rank_idx
            universe.metrics["ranking_score"]  = round(score, 4)
            universe.metrics["on_pareto_front"] = universe.universe_id in pareto_ids
            universe.metrics["rank_sensitivity"] = sensitivity.get(universe.universe_id, {})

        return [u for u, _ in ranked]

    def pareto_data(self, universes: list) -> list[dict]:
        """Return all universes with Pareto metadata for visualization."""
        pareto_ids = self._pareto_frontier(universes)
        result = []
        for u in universes:
            m = u.metrics
            result.append({
                "universe_id":     u.universe_id,
                "name":            u.name,
                "f1":              m.get("f1", 0),
                "recall":          m.get("recall", 0),
                "precision":       m.get("precision", 0),
                "false_positive_rate": m.get("false_positive_rate", 0),
                "total_cost":      m.get("total_cost", 0),
                "ranking_score":   m.get("ranking_score", 0),
                "on_pareto_front": u.universe_id in pareto_ids,
                "rank":            u.rank,
            })
        return result

    def _pareto_frontier(self, universes: list) -> set[str]:
        """
        Non-dominated sorting on objectives:
          maximize F1, maximize Recall, minimize FPR, minimize Cost.

        A solution A dominates B if A is at least as good on ALL objectives
        and strictly better on at least ONE.
        """
        n = len(universes)
        dominated = [False] * n

        def _dom(u, v) -> bool:
            """Returns True if u dominates v."""
            mu, mv = u.metrics, v.metrics
            at_least_as_good = (
                mu.get("f1", 0)     >= mv.get("f1", 0)
                and mu.get("recall", 0) >= mv.get("recall", 0)
                and mu.get("false_positive_rate", 1) <= mv.get("false_positive_rate", 1)
                and mu.get("total_cost", 0) <= mv.get("total_cost", 0)
            )
            strictly_better = (
                mu.get("f1", 0)     > mv.get("f1", 0)
                or mu.get("recall", 0) > mv.get("recall", 0)
                or mu.get("false_positive_rate", 1) < mv.get("false_positive_rate", 1)
                or mu.get("total_cost", 0) < mv.get("total_cost", 0)
            )
            return at_least_as_good and strictly_better

        for i in range(n):
            for j in range(n):
                if i != j and _dom(universes[j], universes[i]):
                    dominated[i] = True
                    break

        return {u.universe_id for i, u in enumerate(universes) if not dominated[i]}

    def _sensitivity(
        self, universes: list, costs_norm: np.ndarray
    ) -> dict[str, dict]:
        """
        Compute rank correlation stability: how does each universe's rank
        change if we shift weights ±20%?
        Returns dict {universe_id: {min_rank, max_rank, rank_variance}}
        """
        weight_variants = [
            (0.50, 0.25, 0.15, 0.10),  # F1-focused
            (0.25, 0.50, 0.15, 0.10),  # Recall-focused
            (0.30, 0.25, 0.35, 0.10),  # FPR-focused
            (0.30, 0.25, 0.15, 0.30),  # Cost-focused
        ]

        all_ranks: dict[str, list[int]] = {u.universe_id: [] for u in universes}

        for wf1, wrec, wfpr, wcost in weight_variants:
            scores = [
                wf1    * u.metrics.get("f1", 0)
                + wrec   * u.metrics.get("recall", 0)
                - wfpr   * u.metrics.get("false_positive_rate", 0)
                - wcost  * costs_norm[i]
                for i, u in enumerate(universes)
            ]
            ranked = sorted(range(len(universes)), key=lambda i: scores[i], reverse=True)
            for rank, idx in enumerate(ranked, start=1):
                all_ranks[universes[idx].universe_id].append(rank)

        result = {}
        for uid, ranks in all_ranks.items():
            result[uid] = {
                "min_rank": min(ranks),
                "max_rank": max(ranks),
                "rank_variance": round(float(np.var(ranks)), 2),
                "rank_stable": (max(ranks) - min(ranks)) <= 1,
            }
        return result
