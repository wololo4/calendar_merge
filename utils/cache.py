import os
import hashlib
from pathlib import Path

from icalendar import Calendar


def _cache_path(cache_dir, key):
    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return cache_root / f"{digest}.ics"


def save_cached_calendar(cache_dir, key, calendar):
    path = _cache_path(cache_dir, key)
    with path.open("wb") as handle:
        handle.write(calendar.to_ical())
    return path


def load_cached_calendar(cache_dir, key):
    path = _cache_path(cache_dir, key)
    if not path.exists():
        return None

    try:
        return Calendar.from_ical(path.read_bytes())
    except Exception:
        return None
