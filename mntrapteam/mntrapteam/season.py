from __future__ import annotations
from datetime import date


def season_bounds(season: int) -> tuple[str, str]:
    """Return inclusive MTA target-year bounds: Sep 1 prior year through Aug 31."""
    return f"{season-1:04d}-09-01", f"{season:04d}-08-31"


def season_for_date(value: str | date) -> int:
    d = date.fromisoformat(value) if isinstance(value, str) else value
    return d.year + 1 if d.month >= 9 else d.year
