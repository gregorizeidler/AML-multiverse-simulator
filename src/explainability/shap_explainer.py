from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import shap as _shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False

from ..ml_universe.model import FEATURE_COLS


@dataclass
class SHAPExplainer:
    """
    Wraps a trained XGBoost model with SHAP TreeExplainer to produce:
      - Global feature importance (mean |SHAP|)
      - Per-transaction SHAP waterfall data
      - Expected value (model baseline)
    """

    model: Any = None
    scaler: Any = None
    _explainer: Any = field(default=None, init=False, repr=False)
    _background: np.ndarray = field(default=None, init=False, repr=False)

    def fit(self, X_background: pd.DataFrame) -> "SHAPExplainer":
        if not _SHAP_AVAILABLE or self.model is None:
            return self

        X = self._prepare(X_background)
        self._background = X
        try:
            self._explainer = _shap.TreeExplainer(self.model, data=X[:200])
        except Exception:
            self._explainer = None
        return self

    def explain_global(self, X: pd.DataFrame, n_samples: int = 500) -> dict:
        if not _SHAP_AVAILABLE or self._explainer is None:
            return self._fallback_global(X)

        X_prep = self._prepare(X.head(n_samples))
        try:
            sv = self._explainer.shap_values(X_prep)
            if isinstance(sv, list):
                sv = sv[1]
            feature_names = self._feature_names(X)
            mean_abs = np.abs(sv).mean(axis=0)
            pairs = sorted(zip(feature_names, mean_abs.tolist()), key=lambda x: x[1], reverse=True)
            return {
                "feature_importance": [{"feature": k, "importance": round(v, 6)} for k, v in pairs],
                "expected_value": float(self._explainer.expected_value if not isinstance(self._explainer.expected_value, list) else self._explainer.expected_value[1]),
                "n_samples": len(X_prep),
                "shap_available": True,
            }
        except Exception as exc:
            return self._fallback_global(X, error=str(exc))

    def explain_transaction(self, row: pd.Series) -> dict:
        if not _SHAP_AVAILABLE or self._explainer is None:
            return self._fallback_local(row)

        X = pd.DataFrame([row])
        X_prep = self._prepare(X)
        feature_names = self._feature_names(X)
        try:
            sv = self._explainer.shap_values(X_prep)
            if isinstance(sv, list):
                sv = sv[1]
            values = sv[0].tolist()
            expected = float(self._explainer.expected_value if not isinstance(self._explainer.expected_value, list) else self._explainer.expected_value[1])
            contributions = [
                {"feature": f, "shap_value": round(v, 6), "feature_value": round(float(X_prep[0, i]), 4)}
                for i, (f, v) in enumerate(zip(feature_names, values))
            ]
            contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            return {
                "tx_id": str(row.get("tx_id", "unknown")),
                "expected_value": expected,
                "prediction": float(expected + sum(v for _, v in zip(feature_names, values))),
                "contributions": contributions[:15],
                "shap_available": True,
            }
        except Exception as exc:
            return self._fallback_local(row, error=str(exc))

    def _prepare(self, X: pd.DataFrame) -> np.ndarray:
        available = [c for c in FEATURE_COLS if c in X.columns]
        X_out = X[available].fillna(0).replace([np.inf, -np.inf], 0)
        if self.scaler is not None:
            return self.scaler.transform(X_out)
        return X_out.values

    def _feature_names(self, X: pd.DataFrame) -> list[str]:
        return [c for c in FEATURE_COLS if c in X.columns]

    def _fallback_global(self, X: pd.DataFrame, error: str = "") -> dict:
        feature_names = self._feature_names(X)
        # Proxy importance: variance of each feature (rough approximation)
        variances = X[[c for c in FEATURE_COLS if c in X.columns]].fillna(0).var().values
        pairs = sorted(zip(feature_names, variances.tolist()), key=lambda x: x[1], reverse=True)
        return {
            "feature_importance": [{"feature": k, "importance": round(v, 6)} for k, v in pairs],
            "expected_value": 0.0,
            "n_samples": len(X),
            "shap_available": False,
            "fallback_reason": error or "shap not installed or model not set",
        }

    def _fallback_local(self, row: pd.Series, error: str = "") -> dict:
        contributions = [
            {"feature": k, "shap_value": float(row.get(k, 0)) * 0.1, "feature_value": float(row.get(k, 0))}
            for k in FEATURE_COLS if k in row.index
        ]
        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        return {
            "tx_id": str(row.get("tx_id", "unknown")),
            "expected_value": 0.0,
            "prediction": float(row.get("xgb_score", row.get("ensemble_score", 0.0))),
            "contributions": contributions[:15],
            "shap_available": False,
            "fallback_reason": error or "shap not installed",
        }
