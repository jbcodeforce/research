"""A simple seen-item store keyed by article guid, used to avoid re-briefing
the same story on consecutive morning runs.

Persisted as ``{"guid": "ISO-8601 last-seen timestamp"}``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SeenStore:
    """Tracks which stories have already been briefed within the recency window."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.entries: dict[str, str] = {}

    def load(self) -> None:
        """Load previously seen items. A corrupt file starts the store empty."""
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.entries = {}
            return
        if isinstance(data, dict):
            self.entries = {
                k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)
            }

    def is_seen(self, guid: str) -> bool:
        return guid in self.entries

    def mark(self, guids: list[str], when: datetime | None = None) -> None:
        """Record the last-seen time for each guid, overwriting any prior value."""
        base = when or datetime.now(timezone.utc)
        for guid in guids:
            self.entries[guid] = base.isoformat()

    def save(self) -> None:
        """Persist the store to disk as JSON."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries), encoding="utf-8")

    def prune(self, keep_days: int = 90, max_entries: int | None = None) -> None:
        """Drop stale entries and, if too large, the oldest ones.

        Two independent caps are applied: entries older than ``keep_days`` are
        removed, then if more than ``max_entries`` remain the oldest (by last
        seen) are discarded first.
        """
        now = datetime.now(timezone.utc)
        kept: dict[str, str] = {}
        for guid, ts in self.entries.items():
            try:
                ts_dt = datetime.fromisoformat(ts)
            except ValueError:
                continue
            if now - ts_dt > timedelta(days=keep_days):
                continue
            kept[guid] = ts
        self.entries = kept
        if max_entries is not None and len(self.entries) > max_entries:
            ordered = sorted(self.entries.items(), key=lambda kv: kv[1])[:max_entries]
            self.entries = dict(ordered)
