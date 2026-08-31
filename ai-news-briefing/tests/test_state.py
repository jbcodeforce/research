"""Tests for ai_news.state: seen-item store (avoid re-briefing the same story)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ai_news.state import SeenStore

T0 = datetime(2026, 8, 30, 7, 0, tzinfo=timezone.utc)


def test_fresh_store_is_empty(tmp_path):
    store = SeenStore(tmp_path / "seen.json")
    store.load()
    assert not store.is_seen("g1")


def test_mark_save_reload_roundtrip(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path)
    store.mark(["g1", "g2"], T0)
    store.save()

    reloaded = SeenStore(path)
    reloaded.load()
    assert reloaded.is_seen("g1")
    assert reloaded.is_seen("g2")
    assert not reloaded.is_seen("g3")


def test_mark_updates_existing_entry(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path)
    store.mark(["g1"], T0)
    store.save()
    store.load()
    store.mark(["g1"], T0 + timedelta(days=1))
    store.save()

    reloaded = SeenStore(path)
    reloaded.load()
    assert reloaded.entries["g1"] == (T0 + timedelta(days=1)).isoformat()


def test_prune_drops_old_entries(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path)
    store.mark(["recent"], T0)
    store.mark(["old"], T0 - timedelta(days=30))
    store.prune(keep_days=14)
    store.save()

    reloaded = SeenStore(path)
    reloaded.load()
    assert reloaded.is_seen("recent")
    assert not reloaded.is_seen("old")


def test_prune_caps_entry_count_oldest_first(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path)
    for i in range(5):
        store.mark(f"g{i}", T0 - timedelta(days=i))
    store.prune(keep_days=999, max_entries=3)
    assert sorted(store.entries) == ["g0", "g1", "g2"]  # the three most recent


def test_load_corrupt_file_starts_fresh(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("{broken")
    store = SeenStore(path)
    store.load()
    assert store.entries == {}
