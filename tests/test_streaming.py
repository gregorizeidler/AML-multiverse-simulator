import asyncio
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from src.streaming.kafka_mock import KafkaMockBroker, KafkaProducer, KafkaConsumer
from src.streaming.stream_processor import StreamProcessor, publish_transactions, TOPICS


def _make_transactions(n=50, seed=0):
    rng = np.random.default_rng(seed)
    accounts = [f"A{i:04d}" for i in range(20)]
    return pd.DataFrame(
        {
            "tx_id": [f"T{i:06d}" for i in range(n)],
            "from_account": rng.choice(accounts, n),
            "to_account": rng.choice(accounts, n),
            "amount": rng.lognormal(7, 1.5, n),
            "timestamp": pd.date_range("2023-01-01", periods=n, freq="30min"),
            "is_illicit": (rng.random(n) < 0.1).tolist(),
            "illicit_typology": [None] * n,
            "is_cross_border": (rng.random(n) < 0.2).tolist(),
        }
    )


def test_broker_publish_consume():
    broker = KafkaMockBroker()
    broker.publish("test.topic", {"key": "value"})
    broker.publish("test.topic", {"key": "value2"})
    msgs = broker.consume("test.topic", group_id="g1")
    assert len(msgs) == 2
    # Second consume returns nothing (already committed)
    msgs2 = broker.consume("test.topic", group_id="g1")
    assert len(msgs2) == 0


def test_broker_multiple_groups():
    broker = KafkaMockBroker()
    broker.publish("t", {"v": 1})
    broker.publish("t", {"v": 2})
    g1 = broker.consume("t", group_id="g1")
    g2 = broker.consume("t", group_id="g2")
    assert len(g1) == 2
    assert len(g2) == 2  # separate offsets


def test_kafka_producer_send_dataframe():
    broker = KafkaMockBroker()
    df = _make_transactions(20)
    producer = KafkaProducer(broker, TOPICS["transactions"])
    count = producer.send_dataframe(df, key_col="tx_id")
    assert count == 20
    assert broker.topic_size(TOPICS["transactions"]) == 20


def test_publish_transactions_helper():
    broker = KafkaMockBroker()
    df = _make_transactions(30)
    total = publish_transactions(df, broker, batch_size=10)
    assert total == 30


def test_stream_processor_sync(transactions, accounts):
    from pathlib import Path
    from src.rule_engine.loader import load_universe_config
    cfg_path = Path("config/universes/universe_balanced.yaml")
    if not cfg_path.exists():
        pytest.skip("Config not found")

    config = load_universe_config(cfg_path)
    broker = KafkaMockBroker()
    df = _make_transactions(100)
    publish_transactions(df, broker)

    processor = StreamProcessor(broker, config)
    stats = processor.run_sync(batch_size=50)
    assert stats.processed == 100
    assert stats.alerted >= 0


def test_stream_processor_async(transactions, accounts):
    from pathlib import Path
    from src.rule_engine.loader import load_universe_config
    cfg_path = Path("config/universes/universe_balanced.yaml")
    if not cfg_path.exists():
        pytest.skip("Config not found")

    config = load_universe_config(cfg_path)
    broker = KafkaMockBroker()
    df = _make_transactions(50)
    publish_transactions(df, broker)

    processor = StreamProcessor(broker, config)
    events = []

    async def collect():
        async for event in processor.run_async(batch_size=25):
            events.append(event)

    asyncio.run(collect())
    assert any(e["type"] == "complete" for e in events)
    assert any(e["type"] == "progress" for e in events)
