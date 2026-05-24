from __future__ import annotations

import pandas as pd

from .behavioral import BehavioralFeatures
from .graph_features import GraphFeatures
from .timeseries import TimeSeriesFeatures
from .transactional import TransactionalFeatures


class FeaturePipeline:
    """
    Runs all feature extractors in sequence and returns an enriched DataFrame.

    Order matters:
      1. Transactional (rolling windows, z-score)
      2. Time-series (cyclic, calendar, account age)
      3. Behavioral (peer-group deviation, anomaly score — uses transactional cols)
      4. Graph (network topology — uses the full edge set)
    """

    def __init__(self) -> None:
        self.transactional = TransactionalFeatures()
        self.timeseries    = TimeSeriesFeatures()
        self.behavioral    = BehavioralFeatures()
        self.graph         = GraphFeatures()

    def run(
        self, transactions: pd.DataFrame, accounts: pd.DataFrame
    ) -> pd.DataFrame:
        df = self.transactional.transform(transactions)
        df = self.timeseries.transform(df)
        df = self.behavioral.transform(df, accounts)
        df = self.graph.transform(df)
        return df

    @property
    def graph_summary(self) -> dict:
        return self.graph.get_graph_summary()
