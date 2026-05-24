from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class BaseTypology(ABC):
    """Abstract base for all money-laundering typologies."""

    name: str
    rng: np.random.Generator = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.rng is None:
            self.rng = np.random.default_rng(42)

    @abstractmethod
    def inject(
        self,
        transactions: pd.DataFrame,
        accounts: pd.DataFrame,
        bad_accounts: list[str],
    ) -> pd.DataFrame:
        """Return a new DataFrame with illicit transactions injected."""

    def _tag(self, df: pd.DataFrame, indices: list[int]) -> pd.DataFrame:
        df = df.copy()
        df.loc[indices, "is_illicit"] = True
        df.loc[indices, "illicit_typology"] = self.name
        return df

    def _next_tx_id(self, df: pd.DataFrame) -> str:
        existing = df["tx_id"].str.extract(r"T(\d+)").astype(int)
        max_id = existing[0].max() + 1
        return f"T{max_id:08d}"

    def _make_tx_ids(self, df: pd.DataFrame, n: int) -> list[str]:
        try:
            existing_nums = df["tx_id"].str.extract(r"T(\d+)")[0].astype(int)
            start = existing_nums.max() + 1
        except Exception:
            start = 99_000_000
        return [f"T{start + i:08d}" for i in range(n)]
