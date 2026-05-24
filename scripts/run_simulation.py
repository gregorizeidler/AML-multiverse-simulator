#!/usr/bin/env python3
"""
AML Multiverse Simulator — main simulation entry point.

Usage:
    python scripts/run_simulation.py [OPTIONS]

Options:
    --customers N         Number of synthetic customers (default: 2000)
    --transactions N      Number of base transactions (default: 20000)
    --seed N              Random seed (default: 42)
    --illicit-ratio F     Fraction of bad-actor accounts (default: 0.05)
    --workers N           Parallel workers (default: 4)
    --window-days N       Backtesting window size in days (default: 30)
    --skip-generation     Reuse existing dataset instead of regenerating
    --no-backtest         Skip backtesting (faster run)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.autopsy.analyzer import FailureAutopsy
from src.backtesting.engine import BacktestingEngine
from src.data_generator.fintech import SyntheticFintech
from src.entity_resolution.resolver import EntityResolver
from src.multiverse.orchestrator import MultiverseOrchestrator
from src.mutation.engine import MutationEngine
from src.optimization.threshold_optimizer import ThresholdOptimizer
from src.recommendation.agent import RecommendationAgent
from src.rule_engine.loader import load_all_configs
from src.sar.generator import SARGenerator
from src.typologies.injector import TypologyInjector

console = Console()

DATA_DIR    = Path(os.getenv("DATA_DIR",    "./data/output"))
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "./data/results"))
CONFIG_DIR  = Path("./config/universes")


@click.command()
@click.option("--customers",       default=int(os.getenv("NUM_CUSTOMERS",   2000)), type=int)
@click.option("--transactions",    default=int(os.getenv("NUM_TRANSACTIONS", 20000)), type=int)
@click.option("--seed",            default=int(os.getenv("RANDOM_SEED",     42)),   type=int)
@click.option("--illicit-ratio",   default=0.05, type=float)
@click.option("--workers",         default=4,    type=int)
@click.option("--window-days",     default=30,   type=int)
@click.option("--skip-generation", is_flag=True)
@click.option("--no-backtest",     is_flag=True)
def main(
    customers, transactions, seed, illicit_ratio,
    workers, window_days, skip_generation, no_backtest,
):
    console.print(Panel.fit(
        "[bold cyan]AML Multiverse Simulator v2[/bold cyan]\n"
        "[dim]Data · Typologies · Features · Multiverse · ML · Streaming · SAR · Backtest[/dim]",
        border_style="cyan",
    ))

    # ── 1. Data generation ────────────────────────────────────────────────────
    if skip_generation and (DATA_DIR / "transactions.parquet").exists():
        console.print("[yellow]↩ Loading existing dataset…[/yellow]")
        fintech = SyntheticFintech.load(DATA_DIR)
    else:
        console.print(f"[cyan]◆ Generating synthetic fintech — {customers:,} customers / {transactions:,} transactions[/cyan]")
        fintech = SyntheticFintech(n_customers=customers, n_transactions=transactions, seed=seed).generate()
        console.print("[cyan]◆ Injecting typologies…[/cyan]")
        injector = TypologyInjector(illicit_account_ratio=illicit_ratio, seed=seed)
        fintech.transactions = injector.inject_all(fintech.transactions, fintech.accounts, fintech.customers)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        fintech.save(DATA_DIR)

    summary = fintech.summary
    console.print(
        f"[green]Dataset ready:[/green] {summary['n_transactions']:,} txns | "
        f"{summary['illicit_transactions']:,} illicit ({summary['illicit_ratio']*100:.2f}%)"
    )

    # ── 2. Entity resolution ───────────────────────────────────────────────────
    console.print("\n[cyan]◆ Running entity resolution…[/cyan]")
    entity_graph = EntityResolver().resolve(fintech.accounts, fintech.customers)
    console.print(
        f"[green]  ✓ {entity_graph.n_entities:,} entities resolved "
        f"({entity_graph.n_accounts_linked:,} accounts linked)[/green]"
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "entity_resolution.json", "w") as fh:
        json.dump(entity_graph.to_dict(), fh, indent=2, default=str)

    # ── 3. Multiverse simulation ───────────────────────────────────────────────
    console.print("\n[cyan]◆ Running multiverse simulation (ML + GNN universes)…[/cyan]")
    orchestrator = MultiverseOrchestrator(config_dir=CONFIG_DIR, n_workers=workers)
    universes = orchestrator.run_all(fintech.transactions, fintech.accounts, customers=fintech.customers)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 4. Autopsy + SAR ──────────────────────────────────────────────────────
    console.print("\n[cyan]◆ Running failure autopsy + SAR generation…[/cyan]")
    autopsy = FailureAutopsy()
    all_sars = []

    for universe in universes:
        if universe.features is None:
            continue

        report = autopsy.analyze(universe.features, universe.config)
        with open(RESULTS_DIR / f"{universe.universe_id}_autopsy.json", "w") as fh:
            json.dump(report, fh, indent=2, default=str)

        if universe.alerts is not None and not universe.alerts.empty:
            universe.alerts.to_parquet(
                RESULTS_DIR / f"{universe.universe_id}_alerts.parquet", index=False
            )
            # SAR generation for each universe
            sar_gen = SARGenerator(universe_id=universe.universe_id)
            sars = sar_gen.generate_all(universe.alerts, universe.features)
            all_sars.extend([s.to_dict() for s in sars])

    with open(RESULTS_DIR / "sar_reports.json", "w") as fh:
        json.dump(all_sars, fh, indent=2, default=str)
    console.print(f"[green]  ✓ Generated {len(all_sars)} SAR report(s)[/green]")

    # ── 5. Backtesting with bootstrap CI ─────────────────────────────────────
    if not no_backtest:
        console.print(f"\n[cyan]◆ Backtesting (bootstrap CI + Mann-Whitney, {window_days}d windows)…[/cyan]")
        configs = load_all_configs(CONFIG_DIR)
        bt_engine = BacktestingEngine(window_days=window_days, min_transactions=30, n_bootstrap=300)
        bt_results = bt_engine.run_all(configs, fintech.transactions, fintech.accounts)
        with open(RESULTS_DIR / "backtesting.json", "w") as fh:
            json.dump([r.to_dict() for r in bt_results], fh, indent=2, default=str)
        console.print(f"[green]  ✓ Backtesting complete — {len(bt_results)} universes[/green]")

    # ── 6. Threshold optimization (best universe only for speed) ──────────────
    console.print("\n[cyan]◆ Running Bayesian threshold optimization…[/cyan]")
    best_for_opt = orchestrator.best_universe()
    opt_results = []
    if best_for_opt and best_for_opt.features is not None:
        try:
            optimizer = ThresholdOptimizer(n_trials=25, seed=seed)
            opt_result = optimizer.optimize(
                best_for_opt.config,
                best_for_opt.features,
                fintech.accounts,
                baseline_score=best_for_opt.metrics.get("ranking_score", 0),
            )
            opt_results = [opt_result.to_dict()]
            console.print(
                f"[green]  ✓ Optimized '{best_for_opt.name}': "
                f"score {opt_result.best_score:.4f} "
                f"(+{opt_result.improvement_over_baseline:.4f})[/green]"
            )
        except Exception as exc:
            console.print(f"[yellow]  ⚠ Optimization skipped: {exc}[/yellow]")
    with open(RESULTS_DIR / "optimization.json", "w") as fh:
        json.dump(opt_results, fh, indent=2, default=str)

    # ── 7. Mutation engine ────────────────────────────────────────────────────
    console.print("\n[cyan]◆ Generating config mutations…[/cyan]")
    mutation_engine = MutationEngine(seed=seed)
    mutations = mutation_engine.evolve(universes, n_survivors=2, n_offspring=3)
    with open(RESULTS_DIR / "mutations.json", "w") as fh:
        json.dump(mutations, fh, indent=2, default=str)

    # ── 8. Recommendations ────────────────────────────────────────────────────
    console.print("[cyan]◆ Generating policy recommendations…[/cyan]")
    agent = RecommendationAgent()
    recommendations = agent.generate(universes)
    with open(RESULTS_DIR / "recommendations.json", "w") as fh:
        json.dump(recommendations, fh, indent=2, default=str)

    # ── 7. Drift detection ────────────────────────────────────────────────────
    console.print("\n[cyan]◆ Running concept drift detection…[/cyan]")
    best = orchestrator.best_universe()
    if best and best.features is not None:
        best.features.to_parquet(RESULTS_DIR / "transactions_with_features.parquet", index=False)
        try:
            from src.drift.detector import DriftDetector
            drift_detector = DriftDetector()
            drift_reports = drift_detector.detect_temporal(best.features, n_windows=4)
            with open(RESULTS_DIR / "drift.json", "w") as fh:
                json.dump([r.to_dict() for r in drift_reports], fh, indent=2, default=str)
            drifted = sum(r.n_features_drifted for r in drift_reports)
            console.print(f"[green]  ✓ Drift detection complete — {drifted} feature drift events[/green]")
        except Exception as exc:
            console.print(f"[yellow]  ⚠ Drift detection skipped: {exc}[/yellow]")

    sim_summary = {
        "dataset": summary,
        "universes": [u.to_summary_dict() for u in universes],
        "best_universe_id": best.universe_id if best else None,
    }
    with open(RESULTS_DIR / "simulation_summary.json", "w") as fh:
        json.dump(sim_summary, fh, indent=2, default=str)

    # ── 8. Results table ──────────────────────────────────────────────────────
    table = Table(title="Universe Ranking", border_style="cyan")
    for col in ["Rank", "Universe", "F1", "Recall", "FPR", "Alerts", "Total Cost"]:
        table.add_column(col, justify="right" if col not in ("Universe",) else "left")

    for u in universes:
        m = u.metrics
        table.add_row(
            f"#{u.rank}", u.name,
            f"{m.get('f1', 0):.3f}",
            f"{m.get('recall', 0):.3f}",
            f"{m.get('false_positive_rate', 0):.3f}",
            str(m.get("n_alerts", 0)),
            f"${m.get('total_cost', 0):,.0f}",
        )

    console.print(table)
    console.print(Panel(
        f"[green]Simulation complete![/green]\n"
        f"Results → [cyan]{RESULTS_DIR}[/cyan]\n"
        f"Best universe: [bold]{best.name if best else 'N/A'}[/bold]\n\n"
        f"[dim]Start API:     [cyan]uvicorn api.main:app --reload --port 8000[/cyan]\n"
        f"Start frontend: [cyan]cd frontend && npm run dev[/cyan]\n"
        f"LLM chat:      [cyan]set OPENAI_API_KEY for GPT-4o-mini responses[/cyan][/dim]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
