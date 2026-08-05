from __future__ import annotations

from datetime import date


def season_for_date(value: date) -> int:
    """Return the MTA target-year ending year for a calendar date.

    The Minnesota target year runs September 1 through August 31.
    For example:
      September 1, 2025 -> 2026 season
      August 31, 2026   -> 2026 season
    """
    if not isinstance(value, date):
        raise TypeError("value must be a datetime.date")

    return value.year + 1 if value.month >= 9 else value.year


def season_bounds(season_year: int) -> tuple[date, date]:
    """Return inclusive start and end dates for an MTA target year."""
    if not isinstance(season_year, int):
        raise TypeError("season_year must be an integer")

    if season_year < 1900 or season_year > 3000:
        raise ValueError("season_year is outside the supported range")

    return (
        date(season_year - 1, 9, 1),
        date(season_year, 8, 31),
    )