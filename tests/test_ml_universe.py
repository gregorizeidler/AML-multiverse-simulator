import numpy as np
import pandas as pd
import pytest

from src.ml_universe.model import AMLModelScorer, FEATURE_COLS


def _make_feature_df(n=300, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {col: rng.random(n) for col in FEATURE_COLS if col != "is_cross_border"},
    )
    df["is_cross_border"] = rng.integers(0, 2, n)
    df["is_illicit"] = (rng.random(n) < 0.08).astype(bool)
    df["timestamp"] = pd.date_range("2023-01-01", periods=n, freq="1h")
    return df


def test_ml_scorer_fit_score():
    df = _make_feature_df(300)
    scorer = AMLModelScorer(seed=42, n_estimators=20)
    result = scorer.fit_score(df)
    assert "xgb_score" in result.columns
    assert "isolation_score" in result.columns
    assert "ensemble_score" in result.columns


def test_ml_scorer_scores_in_range():
    df = _make_feature_df(300)
    scorer = AMLModelScorer(seed=42, n_estimators=20)
    result = scorer.fit_score(df)
    assert result["xgb_score"].between(0, 1).all()
    assert result["isolation_score"].between(0, 1).all()
    assert result["ensemble_score"].between(0, 1).all()


def test_ml_scorer_requires_fit():
    scorer = AMLModelScorer(seed=42)
    df = _make_feature_df(100)
    with pytest.raises(RuntimeError, match="fit"):
        scorer.score(df)


def test_ml_scorer_illicit_score_higher():
    """Illicit transactions should on average have higher ensemble scores."""
    df = _make_feature_df(500, seed=1)
    scorer = AMLModelScorer(seed=42, n_estimators=50)
    result = scorer.fit_score(df)
    illicit_mean = result[result["is_illicit"]]["ensemble_score"].mean()
    legit_mean   = result[~result["is_illicit"]]["ensemble_score"].mean()
    assert illicit_mean >= legit_mean - 0.05  # allow small tolerance
