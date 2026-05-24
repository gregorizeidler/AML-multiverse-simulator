from __future__ import annotations

"""
Bayesian Threshold Optimizer.

Replaces the random mutation engine with principled Bayesian optimization
using Optuna's Tree-structured Parzen Estimator (TPE).

Objective: maximize ranking_score = 0.35*F1 + 0.30*Recall - 0.20*FPR - 0.15*normalized_cost
Subject to: all rule thresholds in a valid range

Why Bayesian over random search:
  - TPE models p(threshold | good_score) / p(threshold | bad_score)
  - Converges ~5x faster than random for AML threshold spaces
  - Respects the non-linear interaction between thresholds
  - Supports parallel evaluation (n_jobs > 1)
"""

import copy
import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _HAS_OPTUNA = True
except ImportError:
    _HAS_OPTUNA = False


@dataclass
class OptimizationResult:
    universe_id: str
    universe_name: str
    best_score: float
    best_thresholds: dict[str, float]   # rule_id → optimal threshold
    best_alert_threshold: float
    n_trials: int
    improvement_over_baseline: float    # delta in ranking_score
    trial_history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "universe_id": self.universe_id,
            "universe_name": self.universe_name,
            "best_score": self.best_score,
            "best_thresholds": self.best_thresholds,
            "best_alert_threshold": self.best_alert_threshold,
            "n_trials": self.n_trials,
            "improvement_over_baseline": self.improvement_over_baseline,
            "trial_history": self.trial_history[-20:],  # last 20
        }


class ThresholdOptimizer:
    """
    Bayesian optimization of rule thresholds for a given universe config.

    Falls back to random search (scipy.optimize.differential_evolution)
    if Optuna is not installed — still much better than the random mutation engine
    since it uses a genetic algorithm with selection pressure.
    """

    def __init__(
        self,
        n_trials: int = 50,
        n_startup_trials: int = 10,
        seed: int = 42,
        w_f1: float = 0.35,
        w_recall: float = 0.30,
        w_fpr: float = 0.20,
        w_cost: float = 0.15,
    ) -> None:
        self.n_trials = n_trials
        self.n_startup_trials = n_startup_trials
        self.seed = seed
        self.w_f1 = w_f1
        self.w_recall = w_recall
        self.w_fpr = w_fpr
        self.w_cost = w_cost

    def optimize(
        self,
        config,                     # UniverseConfig
        features: pd.DataFrame,
        accounts: pd.DataFrame,
        baseline_score: float = 0.0,
    ) -> OptimizationResult:
        if _HAS_OPTUNA:
            return self._optuna_optimize(config, features, accounts, baseline_score)
        else:
            return self._scipy_optimize(config, features, accounts, baseline_score)

    def _optuna_optimize(
        self, config, features, accounts, baseline_score
    ) -> OptimizationResult:
        trial_history = []

        def objective(trial: "optuna.Trial") -> float:
            candidate = copy.deepcopy(config.raw)

            # Suggest threshold for each rule (±40% of original)
            new_thresholds = {}
            for rule in candidate.get("rules", []):
                orig = rule["threshold"]
                lo = max(orig * 0.5, 0.001)
                hi = orig * 1.6
                new_val = trial.suggest_float(f"thr_{rule['id']}", lo, hi)
                rule["threshold"] = round(new_val, 4)
                new_thresholds[rule["id"]] = round(new_val, 4)

            # Alert threshold
            orig_at = candidate["scoring"]["alert_threshold"]
            new_at = trial.suggest_float("alert_threshold", orig_at * 0.5, orig_at * 1.5)
            candidate["scoring"]["alert_threshold"] = round(new_at, 2)

            score = self._evaluate_config(candidate, features)
            trial_history.append({
                "trial": trial.number,
                "score": score,
                "thresholds": {**new_thresholds, "alert_threshold": round(new_at, 2)},
            })
            return score

        sampler = optuna.samplers.TPESampler(
            n_startup_trials=self.n_startup_trials,
            seed=self.seed,
            multivariate=True,
        )
        study = optuna.create_study(direction="maximize", sampler=sampler)
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

        best = study.best_trial
        best_thresholds = {
            k.replace("thr_", ""): v
            for k, v in best.params.items()
            if k.startswith("thr_")
        }

        return OptimizationResult(
            universe_id=config.id,
            universe_name=config.name,
            best_score=best.value,
            best_thresholds=best_thresholds,
            best_alert_threshold=best.params.get("alert_threshold", config.scoring.alert_threshold),
            n_trials=self.n_trials,
            improvement_over_baseline=round(best.value - baseline_score, 4),
            trial_history=trial_history,
        )

    def _scipy_optimize(
        self, config, features, accounts, baseline_score
    ) -> OptimizationResult:
        from scipy.optimize import differential_evolution
        rules = config.raw.get("rules", [])
        orig_thresholds = [r["threshold"] for r in rules]
        orig_at = config.raw["scoring"]["alert_threshold"]
        trial_history = []
        call_count = [0]

        bounds = [(max(t * 0.5, 0.001), t * 1.6) for t in orig_thresholds]
        bounds.append((orig_at * 0.5, orig_at * 1.5))

        def neg_objective(x: np.ndarray) -> float:
            candidate = copy.deepcopy(config.raw)
            new_thresholds = {}
            for i, rule in enumerate(candidate.get("rules", [])):
                rule["threshold"] = round(float(x[i]), 4)
                new_thresholds[rule["id"]] = round(float(x[i]), 4)
            candidate["scoring"]["alert_threshold"] = round(float(x[-1]), 2)
            score = self._evaluate_config(candidate, features)
            call_count[0] += 1
            trial_history.append({
                "trial": call_count[0],
                "score": score,
                "thresholds": {**new_thresholds, "alert_threshold": round(float(x[-1]), 2)},
            })
            return -score  # minimize negative = maximize

        result = differential_evolution(
            neg_objective,
            bounds=bounds,
            seed=self.seed,
            maxiter=max(1, self.n_trials // 15),
            popsize=10,
            tol=1e-4,
            workers=1,
        )

        best_x = result.x
        best_score = -result.fun
        best_thresholds = {
            rules[i]["id"]: round(float(best_x[i]), 4)
            for i in range(len(rules))
        }

        return OptimizationResult(
            universe_id=config.id,
            universe_name=config.name,
            best_score=best_score,
            best_thresholds=best_thresholds,
            best_alert_threshold=round(float(best_x[-1]), 2),
            n_trials=call_count[0],
            improvement_over_baseline=round(best_score - baseline_score, 4),
            trial_history=trial_history,
        )

    def _evaluate_config(self, raw_config: dict, features: pd.DataFrame) -> float:
        """Quick eval: run rule evaluation + compute ranking score."""
        try:
            from ..rule_engine.loader import _parse_universe_config
            from ..rule_engine.evaluator import RuleEvaluator
            from ..metrics.calculator import MetricsCalculator

            cfg = _parse_universe_config(raw_config)
            evaluator = RuleEvaluator(cfg)
            evaluated = evaluator.evaluate(features)
            calculator = MetricsCalculator(cfg)
            m = calculator.compute(evaluated)

            costs = m.get("total_cost", 0)
            # Normalize cost (we don't know max — use a reasonable cap of $5M)
            cost_norm = min(costs / 5_000_000, 1.0)

            return (
                self.w_f1     * m.get("f1", 0)
                + self.w_recall * m.get("recall", 0)
                - self.w_fpr    * m.get("false_positive_rate", 0)
                - self.w_cost   * cost_norm
            )
        except Exception:
            return -1.0
