from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable

import numpy as np
import pandas as pd

from ..rule_engine.evaluator import RuleEvaluator
from ..rule_engine.loader import UniverseConfig
from .kafka_mock import KafkaMockBroker, KafkaConsumer, KafkaProducer, Message

TOPICS = {
    "transactions": "aml.transactions.raw",
    "alerts": "aml.alerts.generated",
    "stats": "aml.stream.stats",
}

# Rolling windows kept in memory per account
_WINDOW_SIZE = 50  # max transactions tracked per account


@dataclass
class StreamStats:
    processed: int = 0
    alerted: int = 0
    illicit_detected: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed(self) -> float:
        return round(time.time() - self.start_time, 2)

    @property
    def throughput(self) -> float:
        elapsed = self.elapsed or 0.001
        return round(self.processed / elapsed, 1)

    def to_dict(self) -> dict:
        return {
            "processed": self.processed,
            "alerted": self.alerted,
            "illicit_detected": self.illicit_detected,
            "elapsed_s": self.elapsed,
            "throughput_tps": self.throughput,
            "alert_rate": round(self.alerted / max(self.processed, 1), 4),
        }


class StreamProcessor:
    """
    Consumes transactions from the Kafka mock broker, applies real-time
    feature computation and rule evaluation, and publishes alerts back
    to the alerts topic.

    Supports async streaming for WebSocket push.
    """

    def __init__(
        self,
        broker: KafkaMockBroker,
        config: UniverseConfig,
        on_alert: Callable[[dict], Any] | None = None,
        on_stats: Callable[[dict], Any] | None = None,
    ) -> None:
        self.broker = broker
        self.config = config
        self.evaluator = RuleEvaluator(config)
        self.on_alert = on_alert
        self.on_stats = on_stats

        self.stats = StreamStats()
        self._account_history: dict[str, deque] = {}
        self._consumer = KafkaConsumer(broker, TOPICS["transactions"], group_id="stream-processor")
        self._alert_producer = KafkaProducer(broker, TOPICS["alerts"])
        self._stats_producer = KafkaProducer(broker, TOPICS["stats"])

    def _enrich(self, tx: dict) -> dict:
        """Compute lightweight rolling features inline for streaming."""
        acct = tx.get("from_account", "")
        if acct not in self._account_history:
            self._account_history[acct] = deque(maxlen=_WINDOW_SIZE)

        history = self._account_history[acct]
        amounts = [h["amount"] for h in history]
        now = pd.Timestamp(tx.get("timestamp", pd.Timestamp.now()))

        # 1h window count
        one_hour_ago = now - pd.Timedelta("1h")
        count_1h = sum(
            1 for h in history
            if pd.Timestamp(h.get("timestamp", now)) >= one_hour_ago
        )

        # 24h amount
        day_ago = now - pd.Timedelta("24h")
        amount_24h = sum(
            h["amount"] for h in history
            if pd.Timestamp(h.get("timestamp", now)) >= day_ago
        )

        # z-score
        if len(amounts) >= 2:
            mean = np.mean(amounts)
            std = np.std(amounts) or 1.0
            zscore = (tx["amount"] - mean) / std
        else:
            zscore = 0.0

        enriched = {
            **tx,
            "tx_count_1h": count_1h,
            "amount_24h": amount_24h,
            "amount_zscore": round(zscore, 4),
            "is_round_amount": int(tx.get("amount", 0) % 1000 == 0),
            "unique_counterparties_7d": len({h.get("to_account") for h in history}),
            "behavioral_anomaly_score": 0.0,
            "betweenness_centrality": 0.0,
            "peer_group_deviation": 0.0,
            "days_since_last_tx": 0.0,
            "log_amount": np.log1p(tx.get("amount", 0)),
        }

        history.append(tx)
        return enriched

    def _process_batch(self, messages: list[Message]) -> list[dict]:
        alerts = []
        rows = [self._enrich(m.value) for m in messages]
        df = pd.DataFrame(rows)
        evaluated = self.evaluator.evaluate(df)

        for _, row in evaluated.iterrows():
            self.stats.processed += 1
            if row.get("is_alerted"):
                self.stats.alerted += 1
                if row.get("is_illicit"):
                    self.stats.illicit_detected += 1

                alert = {
                    "tx_id": row.get("tx_id"),
                    "from_account": row.get("from_account"),
                    "amount": row.get("amount"),
                    "alert_score": row.get("alert_score"),
                    "is_illicit": bool(row.get("is_illicit")),
                    "illicit_typology": row.get("illicit_typology"),
                    "timestamp": str(row.get("timestamp")),
                }
                self._alert_producer.send(alert)
                alerts.append(alert)
                if self.on_alert:
                    self.on_alert(alert)

        stats_payload = self.stats.to_dict()
        self._stats_producer.send(stats_payload)
        if self.on_stats:
            self.on_stats(stats_payload)

        return alerts

    async def run_async(
        self,
        batch_size: int = 100,
        poll_interval: float = 0.01,
    ) -> AsyncIterator[dict]:
        """
        Async generator: yields progress events suitable for WebSocket streaming.
        """
        while True:
            messages = self._consumer.poll(batch_size)
            if messages:
                alerts = self._process_batch(messages)
                event = {
                    "type": "progress",
                    "stats": self.stats.to_dict(),
                    "new_alerts": alerts,
                }
                yield event
            else:
                remaining = self.broker.topic_size(TOPICS["transactions"])
                if remaining == 0:
                    yield {
                        "type": "complete",
                        "stats": self.stats.to_dict(),
                        "message": "Stream processing complete",
                    }
                    break
                await asyncio.sleep(poll_interval)

    def run_sync(self, batch_size: int = 200) -> StreamStats:
        """Synchronous full-consume, returns final stats."""
        while True:
            messages = self._consumer.poll(batch_size)
            if not messages:
                break
            self._process_batch(messages)
        return self.stats


def publish_transactions(
    df: pd.DataFrame,
    broker: KafkaMockBroker,
    delay_per_batch: float = 0.0,
    batch_size: int = 500,
) -> int:
    """Push a DataFrame of transactions into the broker in batches."""
    producer = KafkaProducer(broker, TOPICS["transactions"])
    total = 0
    for start in range(0, len(df), batch_size):
        batch = df.iloc[start : start + batch_size]
        producer.send_dataframe(batch, key_col="tx_id")
        total += len(batch)
        if delay_per_batch > 0:
            time.sleep(delay_per_batch)
    return total
