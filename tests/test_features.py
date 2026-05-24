import numpy as np
import pandas as pd
import pytest

from src.features.transactional import TransactionalFeatures
from src.features.behavioral import BehavioralFeatures
from src.features.graph_features import GraphFeatures
from src.features.pipeline import FeaturePipeline


def test_transactional_features_adds_columns(transactions, accounts):
    tf = TransactionalFeatures()
    result = tf.transform(transactions.head(100))
    assert "tx_count_1h" in result.columns
    assert "amount_24h" in result.columns
    assert "amount_zscore" in result.columns
    assert "days_since_last_tx" in result.columns
    assert "is_round_amount" in result.columns


def test_transactional_no_negatives(transactions):
    tf = TransactionalFeatures()
    result = tf.transform(transactions.head(100))
    assert (result["tx_count_1h"] >= 0).all()
    assert (result["amount_24h"] >= 0).all()


def test_behavioral_features(transactions, accounts):
    tf = TransactionalFeatures()
    df = tf.transform(transactions.head(100))
    bf = BehavioralFeatures()
    result = bf.transform(df, accounts)
    assert "behavioral_anomaly_score" in result.columns
    assert result["behavioral_anomaly_score"].between(0, 1).all()


def test_graph_features_columns(transactions, accounts):
    gf = GraphFeatures()
    result = gf.transform(transactions.head(200))
    assert "betweenness_centrality" in result.columns
    assert "in_cycle" in result.columns
    assert "pass_through_ratio" in result.columns
    assert "fan_out_ratio" in result.columns


def test_feature_pipeline(transactions, accounts):
    pipeline = FeaturePipeline()
    result = pipeline.run(transactions.head(200), accounts)
    expected_cols = [
        "tx_count_1h", "amount_24h", "behavioral_anomaly_score",
        "betweenness_centrality", "in_cycle",
    ]
    for col in expected_cols:
        assert col in result.columns, f"Missing column: {col}"
