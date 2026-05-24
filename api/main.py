from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AML Multiverse Simulator API v3", version="3.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

DATA_DIR    = Path(os.getenv("DATA_DIR",    "./data/output"))
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "./data/results"))
CONFIG_DIR  = Path("./config/universes")


# ── helpers ────────────────────────────────────────────────────────────────

def _j(path: Path) -> Any:
    if not path.exists(): return None
    with open(path) as fh: return json.load(fh)

def _summary() -> dict:
    data = _j(RESULTS_DIR / "simulation_summary.json")
    if not data: raise HTTPException(status_code=503, detail="Run simulation first.")
    return data


# ── health ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "results_ready":       (RESULTS_DIR / "simulation_summary.json").exists(),
        "backtesting_ready":   (RESULTS_DIR / "backtesting.json").exists(),
        "sar_ready":           (RESULTS_DIR / "sar_reports.json").exists(),
        "drift_ready":         (RESULTS_DIR / "drift.json").exists(),
        "entity_res_ready":    (RESULTS_DIR / "entity_resolution.json").exists(),
        "optimization_ready":  (RESULTS_DIR / "optimization.json").exists(),
    }


# ── core ───────────────────────────────────────────────────────────────────

@app.get("/api/summary")
def get_summary():       return _summary()

@app.get("/api/universes")
def list_universes():    return _summary().get("universes", [])

@app.get("/api/universes/{uid}")
def get_universe(uid: str):
    for u in _summary().get("universes", []):
        if u["universe_id"] == uid: return u
    raise HTTPException(404)

@app.get("/api/universes/{uid}/alerts")
def get_alerts(uid: str, limit: int = 200):
    path = RESULTS_DIR / f"{uid}_alerts.parquet"
    if not path.exists(): return []
    df = pd.read_parquet(path).head(limit)
    return df.where(pd.notnull(df), None).to_dict(orient="records")

@app.get("/api/universes/{uid}/autopsy")
def get_autopsy(uid: str): return _j(RESULTS_DIR / f"{uid}_autopsy.json") or {}

@app.get("/api/recommendations")
def get_recs():          return _j(RESULTS_DIR / "recommendations.json") or {}

@app.get("/api/metrics/comparison")
def metrics_comparison():
    return [{"universe_id": u["universe_id"], "name": u["name"], "rank": u["rank"],
             **u.get("metrics", {})} for u in _summary().get("universes", [])]

@app.get("/api/graph")
def get_graph(limit: int = 500):
    path = RESULTS_DIR / "transactions_with_features.parquet"
    if not path.exists(): return {"nodes": [], "edges": []}
    df = pd.read_parquet(path)
    sampled = df.sample(min(limit * 3, len(df)), random_state=42)
    edges = (sampled.groupby(["from_account", "to_account"])
             .agg(weight=("amount", "sum"), count=("tx_id", "count")).reset_index())
    acc_illicit = (df.groupby("from_account")["is_illicit"].any().reset_index()
                   .rename(columns={"from_account": "id", "is_illicit": "is_suspicious"}))
    edge_accs = set(edges["from_account"]) | set(edges["to_account"])
    nodes = acc_illicit[acc_illicit["id"].isin(edge_accs)].head(limit)
    filtered = set(nodes["id"])
    edges = edges[edges["from_account"].isin(filtered) & edges["to_account"].isin(filtered)]
    return {"nodes": nodes.to_dict(orient="records"),
            "edges": edges.rename(columns={"from_account": "source", "to_account": "target"}).to_dict(orient="records")}

@app.get("/api/graph/node/{account_id}")
def get_node_detail(account_id: str, limit: int = 100):
    """Drill-down: all transactions for a specific account."""
    path = RESULTS_DIR / "transactions_with_features.parquet"
    if not path.exists(): raise HTTPException(404)
    df = pd.read_parquet(path)
    txns = df[(df["from_account"] == account_id) | (df["to_account"] == account_id)].head(limit)
    return {
        "account_id": account_id,
        "n_transactions": len(txns),
        "total_sent": float(txns[txns["from_account"] == account_id]["amount"].sum()),
        "total_received": float(txns[txns["to_account"] == account_id]["amount"].sum()),
        "is_illicit": bool(txns["is_illicit"].any()),
        "typologies": txns["illicit_typology"].dropna().unique().tolist(),
        "transactions": txns.where(pd.notnull(txns), None).head(50).to_dict(orient="records"),
    }

@app.get("/api/mutations")
def get_mutations():     return _j(RESULTS_DIR / "mutations.json") or []

@app.get("/api/backtesting")
def get_backtest():      return _j(RESULTS_DIR / "backtesting.json") or []

@app.get("/api/backtesting/{uid}")
def get_backtest_universe(uid: str):
    for r in (_j(RESULTS_DIR / "backtesting.json") or []):
        if r["universe_id"] == uid: return r
    raise HTTPException(404)

@app.get("/api/sar")
def list_sar():
    data = _j(RESULTS_DIR / "sar_reports.json") or []
    return [{k: v for k, v in r.items() if k not in ("narrative", "sample_transactions")} for r in data]

@app.get("/api/sar/{sar_id}")
def get_sar(sar_id: str):
    for r in (_j(RESULTS_DIR / "sar_reports.json") or []):
        if r.get("sar_id") == sar_id: return r
    raise HTTPException(404)


# ── Pareto frontier ────────────────────────────────────────────────────────

@app.get("/api/pareto")
def get_pareto():
    data = _j(RESULTS_DIR / "simulation_summary.json")
    if not data: raise HTTPException(503, "Run simulation first.")
    universes_raw = data.get("universes", [])
    # Include pareto + sensitivity metadata saved during simulation
    return [
        {
            "universe_id": u["universe_id"],
            "name": u["name"],
            "rank": u["rank"],
            "on_pareto_front": u.get("metrics", {}).get("on_pareto_front", False),
            "rank_sensitivity": u.get("metrics", {}).get("rank_sensitivity", {}),
            **{k: v for k, v in u.get("metrics", {}).items()
               if k in ("f1", "recall", "precision", "false_positive_rate", "total_cost", "ranking_score")},
        }
        for u in universes_raw
    ]


# ── Threshold Simulator ────────────────────────────────────────────────────

class ThresholdSimRequest(BaseModel):
    universe_id: str
    thresholds: dict[str, float]   # rule_id → new threshold
    alert_threshold: float | None = None

@app.post("/api/simulate-thresholds")
def simulate_thresholds(req: ThresholdSimRequest):
    feat_path = RESULTS_DIR / "transactions_with_features.parquet"
    if not feat_path.exists():
        raise HTTPException(503, "Run simulation first.")
    try:
        from src.rule_engine.loader import load_universe_config, _parse_universe_config
        from src.rule_engine.evaluator import RuleEvaluator
        from src.metrics.calculator import MetricsCalculator

        cfg = load_universe_config(CONFIG_DIR / f"{req.universe_id}.yaml")
        raw = cfg.raw.copy()

        # Apply threshold overrides
        for rule in raw.get("rules", []):
            if rule["id"] in req.thresholds:
                rule["threshold"] = req.thresholds[rule["id"]]
        if req.alert_threshold is not None:
            raw["scoring"]["alert_threshold"] = req.alert_threshold

        new_cfg = _parse_universe_config(raw)
        df = pd.read_parquet(feat_path)
        evaluator = RuleEvaluator(new_cfg)
        evaluated = evaluator.evaluate(df)
        metrics = MetricsCalculator(new_cfg).compute(evaluated)

        # Ranking score
        cost_norm = min(metrics.get("total_cost", 0) / 5_000_000, 1.0)
        metrics["ranking_score"] = round(
            0.35 * metrics.get("f1", 0)
            + 0.30 * metrics.get("recall", 0)
            - 0.20 * metrics.get("false_positive_rate", 0)
            - 0.15 * cost_norm, 4
        )
        return metrics
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── Entity Resolution ──────────────────────────────────────────────────────

@app.get("/api/entity-resolution")
def get_entity_resolution():
    path = RESULTS_DIR / "entity_resolution.json"
    if path.exists(): return _j(path) or {}
    raise HTTPException(503, "Run simulation first (entity resolution included).")


# ── Optimization ───────────────────────────────────────────────────────────

@app.get("/api/optimization")
def get_optimization(): return _j(RESULTS_DIR / "optimization.json") or []

@app.post("/api/optimize/{uid}")
def run_optimization(uid: str, n_trials: int = 30):
    feat_path = RESULTS_DIR / "transactions_with_features.parquet"
    yaml_path = CONFIG_DIR / f"{uid}.yaml"
    if not feat_path.exists() or not yaml_path.exists():
        raise HTTPException(503, "Run simulation first.")
    try:
        from src.rule_engine.loader import load_universe_config
        from src.optimization.threshold_optimizer import ThresholdOptimizer
        cfg = load_universe_config(yaml_path)
        df = pd.read_parquet(feat_path)
        baseline = cfg.raw.get("scoring", {}).get("ranking_score", 0)
        opt = ThresholdOptimizer(n_trials=n_trials)
        result = opt.optimize(cfg, df, None, baseline_score=baseline)
        return result.to_dict()
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── SHAP ───────────────────────────────────────────────────────────────────

@app.get("/api/shap/{uid}")
def get_shap(uid: str):
    path = RESULTS_DIR / f"{uid}_shap.json"
    if not path.exists():
        if uid != "universe_ml_model":
            return {"global": {"shap_available": False, "feature_importance": [],
                               "fallback_reason": "SHAP only available for ML universe"}}
        _generate_shap(uid)
    return _j(path) or {}

def _generate_shap(uid: str):
    try:
        txn_path = RESULTS_DIR / "transactions_with_features.parquet"
        if not txn_path.exists(): return
        df = pd.read_parquet(txn_path)
        from src.ml_universe.model import AMLModelScorer
        from src.explainability.shap_explainer import SHAPExplainer
        from src.calibration.calibrator import ModelCalibrator
        scorer = AMLModelScorer(seed=42, n_estimators=100)
        scored_df = scorer.fit_score(df)
        explainer = SHAPExplainer(model=scorer._xgb, scaler=scorer._scaler)
        explainer.fit(df)
        global_shap = explainer.explain_global(df)
        y_true   = df["is_illicit"].astype(int).values
        y_scores = scored_df["xgb_score"].values
        calibration = ModelCalibrator().evaluate_before_after(y_scores, y_true)
        result = {"global": global_shap, "calibration": calibration}
        with open(RESULTS_DIR / f"{uid}_shap.json", "w") as fh:
            json.dump(result, fh, default=str)
    except Exception as exc:
        with open(RESULTS_DIR / f"{uid}_shap.json", "w") as fh:
            json.dump({"global": {"shap_available": False, "feature_importance": [],
                                  "fallback_reason": str(exc)}}, fh)


# ── Cases ──────────────────────────────────────────────────────────────────

@app.get("/api/cases/{uid}")
def get_cases(uid: str):
    cache = RESULTS_DIR / f"{uid}_cases.json"
    if cache.exists(): return _j(cache) or []
    alert_path = RESULTS_DIR / f"{uid}_alerts.parquet"
    if not alert_path.exists(): return []
    try:
        from src.alert_clustering.clusterer import AlertClusterer, CLUSTER_FEATURES
        alerts_df = pd.read_parquet(alert_path)
        feat_path = RESULTS_DIR / "transactions_with_features.parquet"
        if feat_path.exists():
            feat_df = pd.read_parquet(feat_path)
            cols = ["tx_id"] + [c for c in CLUSTER_FEATURES if c in feat_df.columns]
            alerts_df = alerts_df.merge(feat_df[cols].drop_duplicates("tx_id"), on="tx_id", how="left")
        cases = AlertClusterer(universe_id=uid).cluster(alerts_df)
        result = [c.to_dict() for c in cases]
        with open(cache, "w") as fh: json.dump(result, fh, default=str)
        return result
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── Drift ──────────────────────────────────────────────────────────────────

@app.get("/api/drift")
def get_drift():
    path = RESULTS_DIR / "drift.json"
    if path.exists(): return _j(path) or []
    try:
        feat_path = RESULTS_DIR / "transactions_with_features.parquet"
        if not feat_path.exists(): return []
        df = pd.read_parquet(feat_path)
        from src.drift.detector import DriftDetector
        reports = DriftDetector().detect_temporal(df, n_windows=4)
        result = [r.to_dict() for r in reports]
        with open(path, "w") as fh: json.dump(result, fh, default=str)
        return result
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── RAG Chat ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

_rag_agent = None

def _get_rag_agent():
    global _rag_agent
    if _rag_agent is None:
        from src.llm.rag_agent import RAGChatAgent
        _rag_agent = RAGChatAgent(results_dir=RESULTS_DIR)
    return _rag_agent

@app.post("/api/chat")
def chat(req: ChatRequest):
    return _get_rag_agent().chat(req.message)

@app.post("/api/chat/reset")
def reset_chat():
    global _rag_agent
    _rag_agent = None
    return {"status": "reset"}


# ── WebSocket ──────────────────────────────────────────────────────────────

@app.websocket("/ws/simulate")
async def simulate_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json({"type": "start", "message": "Initializing streaming simulation…"})
        txn_path = DATA_DIR / "transactions.parquet"
        if not txn_path.exists():
            await websocket.send_json({"type": "error", "message": "No data. Run simulation first."})
            return
        transactions = pd.read_parquet(txn_path)
        await websocket.send_json({"type": "progress",
                                   "message": f"Loaded {len(transactions):,} transactions", "stats": {}})
        from src.rule_engine.loader import load_universe_config
        from src.streaming.kafka_mock import KafkaMockBroker
        from src.streaming.stream_processor import StreamProcessor, publish_transactions
        config = load_universe_config(Path("./config/universes/universe_balanced.yaml"))
        broker = KafkaMockBroker()
        sample = transactions.sample(min(2000, len(transactions)), random_state=42)
        publish_transactions(sample, broker)
        processor = StreamProcessor(broker, config)
        async for event in processor.run_async(batch_size=100, poll_interval=0.01):
            await websocket.send_json(event)
            if event.get("type") == "complete": break
            await asyncio.sleep(0)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try: await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception: pass
