from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import Any

import yaml

from ..rule_engine.loader import UniverseConfig


class MutationEngine:
    """
    Generates mutated variants of existing universe configs.
    Supports threshold perturbation, weight perturbation, and rule toggling.
    """

    MUTATION_TYPES = ["threshold_perturbation", "weight_perturbation", "rule_toggle"]

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def mutate(
        self,
        config: UniverseConfig,
        n_mutations: int = 3,
        mutation_rate: float = 0.3,
    ) -> list[dict]:
        """
        Produce `n_mutations` mutated versions of `config` as raw dicts
        (compatible with YAML serialization).
        """
        mutations = []
        for i in range(n_mutations):
            raw = copy.deepcopy(config.raw)
            mutation_log = []

            for rule in raw.get("rules", []):
                if self.rng.random() < mutation_rate:
                    mutation_type = self.rng.choice(self.MUTATION_TYPES)

                    if mutation_type == "threshold_perturbation":
                        old = rule["threshold"]
                        factor = self.rng.uniform(0.7, 1.4)
                        rule["threshold"] = round(old * factor, 2)
                        mutation_log.append(
                            f"R{rule['id']}: threshold {old} → {rule['threshold']}"
                        )

                    elif mutation_type == "weight_perturbation":
                        old = rule["weight"]
                        delta = self.rng.uniform(-0.5, 0.5)
                        rule["weight"] = round(max(0.1, old + delta), 2)
                        mutation_log.append(
                            f"R{rule['id']}: weight {old} → {rule['weight']}"
                        )

                    elif mutation_type == "rule_toggle" and len(raw["rules"]) > 3:
                        raw["rules"].remove(rule)
                        mutation_log.append(f"R{rule['id']}: toggled OFF")
                        break

            # Mutate scoring thresholds
            if self.rng.random() < mutation_rate:
                old = raw["scoring"]["alert_threshold"]
                raw["scoring"]["alert_threshold"] = round(
                    old * self.rng.uniform(0.8, 1.2), 2
                )
                mutation_log.append(
                    f"alert_threshold: {old} → {raw['scoring']['alert_threshold']}"
                )

            raw["id"] = f"{config.id}_mut_{i+1}"
            raw["name"] = f"{config.name} [Mutation #{i+1}]"
            raw["_mutation_log"] = mutation_log

            mutations.append(raw)

        return mutations

    def save_mutations(
        self, mutations: list[dict], output_dir: str | Path
    ) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for mut in mutations:
            path = output_dir / f"{mut['id']}.yaml"
            with open(path, "w") as fh:
                yaml.safe_dump(mut, fh, default_flow_style=False)
            saved.append(path)
        return saved

    def evolve(
        self,
        universes: list,
        n_survivors: int = 2,
        n_offspring: int = 3,
    ) -> list[dict]:
        """
        Genetic-style evolution: keep top-N universes, mutate each to produce
        offspring configs.
        """
        survivors = sorted(universes, key=lambda u: u.rank or 999)[:n_survivors]
        offspring = []
        for universe in survivors:
            offspring += self.mutate(universe.config, n_mutations=n_offspring)
        return offspring
