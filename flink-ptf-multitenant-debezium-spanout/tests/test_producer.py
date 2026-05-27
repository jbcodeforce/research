"""Unit tests for mock Debezium producer helpers."""

import json
import tempfile
from pathlib import Path

from mt_spanout_kafka.producer import _load_ndjson, _tx_key


def test_load_ndjson_reads_lines() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"a": 1}\n')
        f.write("\n")
        f.write('{"b": 2}\n')
        path = Path(f.name)
    try:
        records = _load_ndjson(path)
        assert records == [{"a": 1}, {"b": 2}]
    finally:
        path.unlink()


def test_tx_key_from_transaction_block() -> None:
    record = json.loads(
        '{"transaction": {"id": "12345:99"}, "after": {"tenant_id": "acme"}}'
    )
    assert _tx_key(record) == "12345:99"


def test_tx_key_from_boundary_event() -> None:
    record = {"status": "END", "id": "67890:11"}
    assert _tx_key(record) == "67890:11"
