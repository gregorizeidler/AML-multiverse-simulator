from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable

import pandas as pd


@dataclass
class Message:
    topic: str
    key: str | None
    value: dict
    timestamp: float = field(default_factory=time.time)
    offset: int = 0


class KafkaMockBroker:
    """
    In-memory Kafka broker. Supports multiple topics and consumer groups.
    All producers/consumers obtained from this broker share the same message store.
    """

    def __init__(self) -> None:
        self._topics: dict[str, deque[Message]] = defaultdict(deque)
        self._offsets: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def publish(self, topic: str, value: dict, key: str | None = None) -> int:
        offset = len(self._topics[topic])
        msg = Message(topic=topic, key=key, value=value, offset=offset)
        self._topics[topic].append(msg)
        return offset

    def consume(
        self,
        topic: str,
        group_id: str = "default",
        max_messages: int | None = None,
    ) -> list[Message]:
        committed = self._offsets[group_id][topic]
        messages = list(self._topics[topic])[committed:]
        if max_messages is not None:
            messages = messages[:max_messages]
        self._offsets[group_id][topic] += len(messages)
        return messages

    def topic_size(self, topic: str) -> int:
        return len(self._topics[topic])

    def list_topics(self) -> list[str]:
        return list(self._topics.keys())


class KafkaProducer:
    def __init__(self, broker: KafkaMockBroker, topic: str) -> None:
        self.broker = broker
        self.topic = topic

    def send(self, value: dict, key: str | None = None) -> int:
        return self.broker.publish(self.topic, value, key)

    def send_dataframe(self, df: pd.DataFrame, key_col: str | None = None) -> int:
        count = 0
        for _, row in df.iterrows():
            key = str(row[key_col]) if key_col and key_col in row else None
            self.send(row.to_dict(), key=key)
            count += 1
        return count


class KafkaConsumer:
    def __init__(
        self,
        broker: KafkaMockBroker,
        topic: str,
        group_id: str = "aml-consumer",
    ) -> None:
        self.broker = broker
        self.topic = topic
        self.group_id = group_id

    def poll(self, max_messages: int = 100) -> list[Message]:
        return self.broker.consume(self.topic, self.group_id, max_messages)

    async def stream(
        self,
        batch_size: int = 50,
        poll_interval: float = 0.05,
        on_batch: Callable[[list[Message]], Any] | None = None,
    ) -> AsyncIterator[list[Message]]:
        """Async generator that yields batches as they arrive."""
        while True:
            batch = self.poll(batch_size)
            if batch:
                if on_batch:
                    on_batch(batch)
                yield batch
            else:
                await asyncio.sleep(poll_interval)
                pending = self.broker.topic_size(self.topic)
                if pending == 0:
                    break
