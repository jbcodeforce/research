"""Smoke tests for deployment assets."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "cc-flink"


def test_sql_assets_exist():
    expected = [
        "01_ddl_source.sql",
        "02_ddl_sink_v1.sql",
        "03_dml_v1_aggregate.sql",
        "04_ddl_snapshot.sql",
        "05_ddl_sink_v2.sql",
        "06_dml_v2_handoff.sql",
        "06b_dml_v2_handoff_fallback.sql",
        "deploy.sh",
    ]
    for name in expected:
        assert (ASSETS / name).is_file(), name


def test_v2_sql_contains_specific_offsets_placeholder():
    sql = (ASSETS / "06_dml_v2_handoff.sql").read_text()
    assert "${SPECIFIC_OFFSETS}" in sql
    assert "FULL OUTER JOIN" in sql


def test_v1_sink_is_upsert():
    sql = (ASSETS / "02_ddl_sink_v1.sql").read_text()
    assert "changelog.mode" in sql
    assert "upsert" in sql
    assert "PRIMARY KEY" in sql
