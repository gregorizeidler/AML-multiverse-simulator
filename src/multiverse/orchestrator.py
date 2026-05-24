from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

from ..rule_engine.loader import UniverseConfig, load_all_configs
from ..ranking.ranker import UniverseRanker
from .runner import UniverseRunner
from .universe import Universe

console = Console()


class MultiverseOrchestrator:
    """
    Runs all universe configurations in parallel and produces a ranked
    list of results.
    """

    def __init__(
        self,
        config_dir: str | Path,
        n_workers: int = 4,
    ) -> None:
        self.config_dir = Path(config_dir)
        self.n_workers = n_workers
        self.universes: list[Universe] = []
        self.configs: list[UniverseConfig] = []

    def load_configs(self) -> "MultiverseOrchestrator":
        self.configs = load_all_configs(self.config_dir)
        console.print(
            f"[cyan]Loaded {len(self.configs)} universe configs[/cyan]"
        )
        return self

    def run_all(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        customers: pd.DataFrame | None = None,
    ) -> list[Universe]:
        if not self.configs:
            self.load_configs()

        # Entity resolution — once for all universes
        entity_graph = None
        if customers is not None:
            try:
                from ..entity_resolution.resolver import EntityResolver
                entity_graph = EntityResolver().resolve(accounts, customers)
                console.print(
                    f"[cyan]Entity resolution: {entity_graph.n_entities:,} entities "
                    f"from {len(accounts):,} accounts "
                    f"({entity_graph.n_accounts_linked:,} linked)[/cyan]"
                )
            except Exception as exc:
                console.print(f"[yellow]Entity resolution skipped: {exc}[/yellow]")

        results: list[Universe] = []

        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            tasks = {
                cfg.id: progress.add_task(f"[yellow]{cfg.name}", total=None)
                for cfg in self.configs
            }

            def _run_one(cfg: UniverseConfig) -> Universe:
                runner = UniverseRunner(cfg)
                return runner.run(transactions, accounts, entity_graph=entity_graph)

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.n_workers
            ) as executor:
                future_to_cfg = {
                    executor.submit(_run_one, cfg): cfg
                    for cfg in self.configs
                }
                for future in concurrent.futures.as_completed(future_to_cfg):
                    cfg = future_to_cfg[future]
                    try:
                        universe = future.result()
                        results.append(universe)
                        progress.update(tasks[cfg.id], completed=True)
                        console.print(
                            f"[green]✓[/green] {cfg.name} — "
                            f"F1={universe.metrics.get('f1', 0):.3f} | "
                            f"Alerts={universe.metrics.get('n_alerts', 0)}"
                        )
                    except Exception as exc:
                        console.print(
                            f"[red]✗ {cfg.name} failed: {exc}[/red]"
                        )

        # Rank universes
        ranker = UniverseRanker()
        self.universes = ranker.rank(results)
        return self.universes

    def best_universe(self) -> Universe | None:
        return self.universes[0] if self.universes else None
