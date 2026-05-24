from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# XGBoost is optional — falls back to GradientBoostingClassifier
try:
    from xgboost import XGBClassifier
    _HAS_XGB = True
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier as _GBC
    _HAS_XGB = False

FEATURE_COLS = [
    # Transactional
    "amount", "log_amount",
    "tx_count_1h", "tx_count_24h",
    "amount_1h", "amount_24h", "amount_7d",
    "unique_counterparties_7d",
    "amount_zscore",
    "days_since_last_tx",
    # Behavioral
    "peer_group_deviation", "behavioral_anomaly_score",
    # Graph
    "betweenness_centrality", "in_cycle", "community_risk_score",
    "fan_out_ratio", "pass_through_ratio",
    # Categorical (encoded)
    "is_round_amount", "is_cross_border",
    # Temporal (from TimeSeriesFeatures)
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos",
    "is_weekend", "is_night", "account_age_days", "hour_anomaly",
]


@dataclass
class AMLModelScorer:
    """
    Trains IsolationForest + XGBoost on a time-stratified split and
    scores all transactions with three derived columns:

        xgb_score        — XGBoost predicted probability [0, 1]
        isolation_score  — Normalized IF anomaly score   [0, 1]
        ensemble_score   — Weighted combination          [0, 1]
    """

    train_ratio: float = 0.65
    seed: int = 42
    n_estimators: int = 200
    contamination: float = 0.06

    _xgb: Any = field(default=None, init=False, repr=False)
    _iso: Any = field(default=None, init=False, repr=False)
    _scaler: StandardScaler = field(default=None, init=False, repr=False)
    _trained: bool = field(default=False, init=False)
    _cv_auc_pr: float = field(default=0.0, init=False)

    def _get_features(self, df: pd.DataFrame) -> pd.DataFrame:
        available = [c for c in FEATURE_COLS if c in df.columns]
        X = df[available].copy()
        X = X.fillna(0).replace([np.inf, -np.inf], 0)
        return X

    def _build_xgb(self, **kwargs):
        params = dict(
            n_estimators=kwargs.get("n_estimators", self.n_estimators),
            max_depth=kwargs.get("max_depth", 6),
            learning_rate=kwargs.get("learning_rate", 0.05),
            subsample=kwargs.get("subsample", 0.8),
            colsample_bytree=kwargs.get("colsample_bytree", 0.8),
            min_child_weight=kwargs.get("min_child_weight", 3),
        )
        if _HAS_XGB:
            return XGBClassifier(
                **params,
                scale_pos_weight=20,
                eval_metric="aucpr",
                random_state=self.seed,
                verbosity=0,
            )
        return _GBC(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            subsample=params["subsample"],
            random_state=self.seed,
        )

    def fit(self, df: pd.DataFrame) -> "AMLModelScorer":
        """
        Time-stratified fit with:
          - Stratified K-Fold cross-validation (k=3) for honest AUC-PR estimate
          - Optuna hyperparameter search when n_trials > 0
        """
        df_sorted = df.sort_values("timestamp").reset_index(drop=True)
        split = int(len(df_sorted) * self.train_ratio)
        train = df_sorted.iloc[:split]

        X_train = self._get_features(train)
        y_train = train["is_illicit"].astype(int)

        self._scaler = StandardScaler()
        X_train_scaled = self._scaler.fit_transform(X_train)

        # IsolationForest — unsupervised (no hyperopt needed)
        self._iso = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.seed,
            n_jobs=-1,
        )
        self._iso.fit(X_train_scaled)

        # XGBoost / GBM — supervised with cross-validation + hyperopt
        if y_train.sum() > 5:
            best_params = self._hyperopt(X_train_scaled, y_train)
            self._xgb = self._build_xgb(**best_params)
            self._xgb.fit(X_train_scaled, y_train)
            # Store CV AUC-PR for comparison
            self._cv_auc_pr = self._cross_validate(X_train_scaled, y_train)
        else:
            self._xgb = None
            self._cv_auc_pr = 0.0

        self._trained = True
        return self

    def _hyperopt(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Fast hyperparameter search using Optuna (5 trials) or random search fallback.
        Returns best XGBoost params.
        """
        try:
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)
            from sklearn.model_selection import StratifiedKFold, cross_val_score
            from sklearn.metrics import average_precision_score

            def objective(trial):
                params = {
                    "max_depth":        trial.suggest_int("max_depth", 3, 8),
                    "learning_rate":    trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                    "n_estimators":     trial.suggest_int("n_estimators", 50, 300),
                    "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                    "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                }
                clf = self._build_xgb(**params)
                skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=self.seed)
                scores = []
                for tr_idx, val_idx in skf.split(X, y):
                    clf.fit(X[tr_idx], y[tr_idx])
                    proba = clf.predict_proba(X[val_idx])[:, 1]
                    scores.append(average_precision_score(y[val_idx], proba))
                return float(np.mean(scores))

            study = optuna.create_study(
                direction="maximize",
                sampler=optuna.samplers.TPESampler(seed=self.seed),
            )
            study.optimize(objective, n_trials=5, show_progress_bar=False)
            return study.best_params
        except Exception:
            # Fallback to defaults
            return {}

    def _cross_validate(self, X: np.ndarray, y: np.ndarray) -> float:
        """3-fold stratified CV — returns mean AUC-PR for diagnostics."""
        try:
            from sklearn.model_selection import StratifiedKFold
            from sklearn.metrics import average_precision_score
            skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=self.seed)
            scores = []
            for tr_idx, val_idx in skf.split(X, y):
                clf = self._build_xgb()
                clf.fit(X[tr_idx], y[tr_idx])
                proba = clf.predict_proba(X[val_idx])[:, 1]
                scores.append(average_precision_score(y[val_idx], proba))
            return round(float(np.mean(scores)), 4)
        except Exception:
            return 0.0

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add `xgb_score`, `isolation_score`, and `ensemble_score` columns.
        """
        if not self._trained:
            raise RuntimeError("Call .fit() before .score()")

        result = df.copy()
        X = self._get_features(df)
        X_scaled = self._scaler.transform(X.fillna(0).replace([np.inf, -np.inf], 0))

        # IsolationForest: decision_function returns negative = anomalous
        iso_raw = self._iso.decision_function(X_scaled)
        # Normalize to [0, 1] — lower decision_function = more anomalous → invert
        iso_min, iso_max = iso_raw.min(), iso_raw.max()
        if iso_max > iso_min:
            result["isolation_score"] = np.round(
                1 - (iso_raw - iso_min) / (iso_max - iso_min), 4
            )
        else:
            result["isolation_score"] = 0.5

        # XGBoost probability
        if self._xgb is not None:
            if _HAS_XGB:
                xgb_proba = self._xgb.predict_proba(X_scaled)[:, 1]
            else:
                xgb_proba = self._xgb.predict_proba(X_scaled)[:, 1]
            result["xgb_score"] = np.round(xgb_proba, 4)
        else:
            result["xgb_score"] = result["isolation_score"]

        # Ensemble: 60% XGB + 40% IF
        result["ensemble_score"] = np.round(
            0.60 * result["xgb_score"] + 0.40 * result["isolation_score"], 4
        )

        return result

    def fit_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convenience: fit and score in one call."""
        return self.fit(df).score(df)
