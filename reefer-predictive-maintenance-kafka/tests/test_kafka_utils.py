"""Kafka client helper tests."""

from reefer_pm_kafka.kafka_utils import normalize_bootstrap_servers


def test_localhost_normalized_to_ipv4():
    assert normalize_bootstrap_servers("localhost:9092") == "127.0.0.1:9092"


def test_multiple_brokers():
    assert (
        normalize_bootstrap_servers("localhost:9092, ::1:9093")
        == "127.0.0.1:9092,127.0.0.1:9093"
    )
