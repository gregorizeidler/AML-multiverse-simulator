from __future__ import annotations

import pandas as pd

from ..features.pipeline import FeaturePipeline
from ..metrics.calculator import MetricsCalculator
from ..rule_engine.alert_manager import AlertManager
from ..rule_engine.evaluator import RuleEvaluator
from ..rule_engine.loader import UniverseConfig
from .universe import Universe

ML_UNIVERSE_ID  = "universe_ml_model"
GNN_UNIVERSE_ID = "universe_gnn"


class UniverseRunner:
    """
    Runs a single universe end-to-end:
      1. Feature pipeline (transactional + time-series + behavioral + graph)
      2. Entity resolution enrichment (entity_risk, entity_n_accounts)
      3. ML scoring (ML universe) or GNN scoring (GNN universe)
      4. Rule evaluation
      5. Alert generation
      6. Metrics computation
    """

    def __init__(self, config: UniverseConfig) -> None:
        self.config = config

    def run(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        entity_graph=None,      # optional EntityGraph for enrichment
    ) -> Universe:
        universe = Universe(config=self.config)

        # Feature engineering
        pipeline = FeaturePipeline()
        features = pipeline.run(transactions, accounts)
        universe.graph_summary = pipeline.graph_summary

        # Entity resolution enrichment
        if entity_graph is not None:
            features = entity_graph.enrich_transactions(features)

        # Universe-specific ML scoring
        if self.config.id == ML_UNIVERSE_ID:
            features = self._apply_ml_scores(features)
        elif self.config.id == GNN_UNIVERSE_ID:
            features = self._apply_gnn_scores(features, accounts)

        # Rule evaluation
        evaluator = RuleEvaluator(self.config)
        evaluated = evaluator.evaluate(features)
        universe.features = evaluated

        # Alert generation
        alert_mgr = AlertManager(self.config)
        universe.alerts = alert_mgr.build_alerts(evaluated)

        # Metrics
        calculator = MetricsCalculator(self.config)
        universe.metrics = calculator.compute(evaluated)

        return universe

    def _apply_ml_scores(self, features: pd.DataFrame) -> pd.DataFrame:
        try:
            from ..ml_universe.model import AMLModelScorer
            scorer = AMLModelScorer(seed=42)
            features = scorer.fit_score(features)
        except Exception:
            features["xgb_score"] = features.get("behavioral_anomaly_score", 0.0)
            features["isolation_score"] = features.get("behavioral_anomaly_score", 0.0)
            features["ensemble_score"] = features.get("behavioral_anomaly_score", 0.0)
        return features

    def _apply_gnn_scores(self, features: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
        try:
            from ..gnn_universe.model import GNNScorer
            scorer = GNNScorer(seed=42)
            features = scorer.fit_score(features, accounts)
        except Exception:
            features["gnn_score"] = features.get("behavioral_anomaly_score", 0.0)
        return features
