from __future__ import annotations

import threading
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd

# Hard cap: stop cycle search after this many cycles found
_MAX_CYCLES = 5_000
# Betweenness sample cap: don't use more than this many pivot nodes
_BC_K_CAP = 100


class GraphFeatures:
    """
    Builds a directed transaction graph and computes structural features
    for each account: centrality, cycle membership, community risk, and
    pass-through ratio.
    """

    def __init__(self, min_edge_amount: float = 0.0) -> None:
        self.min_edge_amount = min_edge_amount
        self.graph: nx.DiGraph | None = None

    def build_graph(self, transactions: pd.DataFrame) -> nx.DiGraph:
        edges = transactions[transactions["amount"] > self.min_edge_amount][
            ["from_account", "to_account", "amount"]
        ]
        G = nx.DiGraph()
        G.add_nodes_from(
            set(transactions["from_account"]) | set(transactions["to_account"])
        )
        for row in edges.itertuples(index=False):
            G.add_edge(row.from_account, row.to_account,
                       weight=row.weight, count=row.count)
        self.graph = G
        return G

    def transform(self, transactions: pd.DataFrame) -> pd.DataFrame:
        G = self.build_graph(transactions)
        df = transactions.copy()

        betweenness = self._betweenness_centrality(G)
        in_cycle = self._cycle_membership(G)
        community_risk = self._community_risk(G, transactions)
        fan_out_ratio = self._fan_out_ratio(G)
        pass_through_ratio = self._pass_through_ratio(G)

        df["betweenness_centrality"] = df["from_account"].map(betweenness).fillna(0)
        df["in_cycle"] = df["from_account"].map(in_cycle).fillna(0).astype(int)
        df["community_risk_score"] = df["from_account"].map(community_risk).fillna(0)
        df["fan_out_ratio"] = df["from_account"].map(fan_out_ratio).fillna(1.0)
        df["pass_through_ratio"] = df["from_account"].map(pass_through_ratio).fillna(0.0)

        return df

    def _betweenness_centrality(self, G: nx.DiGraph) -> dict[str, float]:
        if len(G) == 0:
            return {}
        G_undirected = G.to_undirected()
        try:
            k = min(_BC_K_CAP, len(G))
            bc = nx.betweenness_centrality(G_undirected, normalized=True, k=k)
        except Exception:
            bc = {n: 0.0 for n in G.nodes()}
        return bc

    def _cycle_membership(self, G: nx.DiGraph) -> dict[str, int]:
        """
        A node is in a cycle iff it belongs to a strongly connected component
        of size > 1. This is exact, O(V+E) via Tarjan's SCC, and avoids the
        NP-hard simple_cycles enumeration entirely.
        """
        nodes_in_cycle: set[str] = set()
        try:
            for scc in nx.strongly_connected_components(G):
                if len(scc) > 1:
                    nodes_in_cycle.update(scc)
        except Exception:
            pass
        return {n: (1 if n in nodes_in_cycle else 0) for n in G.nodes()}

    def _community_risk(
        self, G: nx.DiGraph, transactions: pd.DataFrame
    ) -> dict[str, float]:
        if len(G) == 0:
            return {}

        G_undirected = G.to_undirected()
        try:
            communities = list(nx.community.louvain_communities(G_undirected, seed=42))
        except Exception:
            communities = [{n} for n in G.nodes()]

        # Fraction of illicit txns in each community
        illicit_by_account: dict[str, float] = (
            transactions.groupby("from_account")["is_illicit"]
            .mean()
            .to_dict()
        )

        node_to_community_risk: dict[str, float] = {}
        for community in communities:
            community = list(community)
            scores = [illicit_by_account.get(n, 0.0) for n in community]
            risk = float(np.mean(scores)) if scores else 0.0
            for node in community:
                node_to_community_risk[node] = round(risk, 4)

        return node_to_community_risk

    def _fan_out_ratio(self, G: nx.DiGraph) -> dict[str, float]:
        ratios = {}
        for node in G.nodes():
            out_degree = G.out_degree(node)
            in_degree = G.in_degree(node)
            ratios[node] = round(out_degree / max(in_degree, 1), 4)
        return ratios

    def _pass_through_ratio(self, G: nx.DiGraph) -> dict[str, float]:
        ratios = {}
        for node in G.nodes():
            total_in = sum(
                data["weight"] for _, _, data in G.in_edges(node, data=True)
            )
            total_out = sum(
                data["weight"] for _, _, data in G.out_edges(node, data=True)
            )
            if total_in > 0:
                ratios[node] = round(min(total_out / total_in, 1.0), 4)
            else:
                ratios[node] = 0.0
        return ratios

    def get_graph_summary(self) -> dict:
        if self.graph is None:
            return {}
        G = self.graph
        return {
            "n_nodes": G.number_of_nodes(),
            "n_edges": G.number_of_edges(),
            "density": round(nx.density(G), 6),
            "n_weakly_connected_components": nx.number_weakly_connected_components(G),
        }
