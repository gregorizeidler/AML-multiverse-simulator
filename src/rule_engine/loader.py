from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RuleConfig:
    id: str
    name: str
    field: str
    operator: str
    threshold: float
    weight: float
    alert_level: str
    typologies: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ScoringConfig:
    method: str = "weighted_sum"
    alert_threshold: float = 2.5
    high_risk_threshold: float = 5.0


@dataclass
class CostModel:
    investigation_cost_per_alert: float = 150.0
    missed_laundering_cost_per_txn: float = 50_000.0


@dataclass
class UniverseConfig:
    id: str
    name: str
    description: str
    rules: list[RuleConfig]
    scoring: ScoringConfig
    cost_model: CostModel
    raw: dict = field(default_factory=dict, repr=False)


def load_universe_config(path: str | Path) -> UniverseConfig:
    path = Path(path)
    with open(path) as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)

    rules = [
        RuleConfig(
            id=r["id"],
            name=r["name"],
            field=r["field"],
            operator=r["operator"],
            threshold=float(r["threshold"]),
            weight=float(r["weight"]),
            alert_level=r["alert_level"],
            typologies=r.get("typologies", []),
            description=r.get("description", ""),
        )
        for r in raw.get("rules", [])
    ]

    scoring_raw = raw.get("scoring", {})
    scoring = ScoringConfig(
        method=scoring_raw.get("method", "weighted_sum"),
        alert_threshold=float(scoring_raw.get("alert_threshold", 2.5)),
        high_risk_threshold=float(scoring_raw.get("high_risk_threshold", 5.0)),
    )

    cost_raw = raw.get("cost_model", {})
    cost_model = CostModel(
        investigation_cost_per_alert=float(
            cost_raw.get("investigation_cost_per_alert", 150.0)
        ),
        missed_laundering_cost_per_txn=float(
            cost_raw.get("missed_laundering_cost_per_txn", 50_000.0)
        ),
    )

    return UniverseConfig(
        id=raw["id"],
        name=raw["name"],
        description=raw.get("description", ""),
        rules=rules,
        scoring=scoring,
        cost_model=cost_model,
        raw=raw,
    )


def _parse_universe_config(raw: dict) -> UniverseConfig:
    """Parse a raw dict (not from file) into a UniverseConfig. Used by optimizer."""
    rules = [
        RuleConfig(
            id=r["id"],
            name=r.get("name", r["id"]),
            field=r["field"],
            operator=r["operator"],
            threshold=float(r["threshold"]),
            weight=float(r["weight"]),
            alert_level=r.get("alert_level", "medium"),
            typologies=r.get("typologies", []),
            description=r.get("description", ""),
        )
        for r in raw.get("rules", [])
    ]
    scoring_raw = raw.get("scoring", {})
    scoring = ScoringConfig(
        method=scoring_raw.get("method", "weighted_sum"),
        alert_threshold=float(scoring_raw.get("alert_threshold", 2.5)),
        high_risk_threshold=float(scoring_raw.get("high_risk_threshold", 5.0)),
    )
    cost_raw = raw.get("cost_model", {})
    cost_model = CostModel(
        investigation_cost_per_alert=float(cost_raw.get("investigation_cost_per_alert", 150.0)),
        missed_laundering_cost_per_txn=float(cost_raw.get("missed_laundering_cost_per_txn", 50_000.0)),
    )
    return UniverseConfig(
        id=raw.get("id", "optimized"),
        name=raw.get("name", "Optimized"),
        description=raw.get("description", ""),
        rules=rules,
        scoring=scoring,
        cost_model=cost_model,
        raw=raw,
    )


def load_all_configs(config_dir: str | Path) -> list[UniverseConfig]:
    config_dir = Path(config_dir)
    return [
        load_universe_config(p)
        for p in sorted(config_dir.glob("universe_*.yaml"))
    ]
