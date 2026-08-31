"""Shared feed helpers: URL normalization and date parsing.

These live here (rather than in models or sources) to keep a single source of
truth for both modules and avoid an import cycle: sources imports from models,
and models needs the normalization used to build Article dedup keys.
"""

from __future__ import annotations

import email.utils
import re
from datetime import datetime, timezone

# Query parameters that are almost always tracking/analytics noise. Dropping
# them lets us treat "same story seen via different syndication links" as one
# story for dedup purposes.
TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "gcc",
        "gc",
        "gclsrc",
        "fbclid",
        "igshid",
        "mc_",
        "_ga",
        "_gl",
        "xs",
    }
)

_PARAM_SPLIT = re.compile(r"[&?]")


def normalize_url(url: str) -> str:
    """Reduce a URL to a canonical comparison key.

    Lower-cases the host, drops the fragment and any tracking params. The key
    is what the dedup layer uses, so being aggressive here is the point.
    """
    if not url:
        return url
    # Strip the fragment and any URL fragment/section markers first so the host
    # regex is not confused.
    url = url.split("#", 1)[0].split(";", 1)[0]

    match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.+-]*)://([^/?#]+)(/.*)?$", url, re.IGNORECASE)
    if not match:
        return url
    scheme, host, path = match.group(1), match.group(2), match.group(3) or "/"
    host = host.lower()

    if path.startswith("?"):
        params = [p for p in _PARAM_SPLIT.split(path)[1:] if p and p.split("=")[0] not in TRACKING_PARAMS]
        path = ("?" + "&".join(params)) if params else ""
    return f"{scheme}://{host}{path}"


def parse_feed_date(value) -> datetime | None:
    """Parse a common RSS/Atom date string to a UTC-aware datetime.

    Handles RFC 822 (``Fri, 29 Aug 2026 14:00:00 +0000``) and ISO 8601
    (``2026-08-29T08:00:00Z`` / ``...+05:30``). Naive ISO datetimes are assumed
    to be UTC. Returns ``None`` when the value cannot be parsed.
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None

    # RFC 822 / RFC 2822 first (also covers the "-0000" mailbox hack feeds use).
    try:
        dt = email.utils.parsedate_to_datetime(text)
        if dt is not None:
            return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass

    # ISO 8601: normalize a trailing "Z" (not accepted by fromisoformat on 3.10).
    iso = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
