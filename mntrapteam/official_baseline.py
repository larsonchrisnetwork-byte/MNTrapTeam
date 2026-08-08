from __future__ import annotations

from datetime import datetime
import re


DATE_PATTERNS = (
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b"),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
)


def ensure_schema(database) -> None:
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS official_season_baselines(
            shooter_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            official_through_date TEXT NOT NULL DEFAULT '',
            singles_targets INTEGER NOT NULL DEFAULT 0,
            singles_hits INTEGER NOT NULL DEFAULT 0,
            handicap_targets INTEGER NOT NULL DEFAULT 0,
            handicap_hits INTEGER NOT NULL DEFAULT 0,
            doubles_targets INTEGER NOT NULL DEFAULT 0,
            doubles_hits INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'MyATA',
            PRIMARY KEY (shooter_id, season)
        )
        """
    )


def _iso_date(text: str) -> str:
    value = str(text or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def official_through_date_from_detail_rows(rows) -> str:
    """Return the newest dated event visible in a MyATA Score Details table."""
    found = []
    for cells in rows:
        for cell in cells:
            text = str(cell or "")
            for pattern in DATE_PATTERNS:
                match = pattern.search(text)
                if not match:
                    continue
                value = _iso_date(match.group(1))
                if value:
                    found.append(value)
    return max(found) if found else ""


def save_baseline(
    database,
    shooter_id: int,
    season: int,
    totals,
    official_through_date: str = "",
    source: str = "MyATA official rendered detail",
) -> None:
    ensure_schema(database)
    database.execute(
        """
        INSERT INTO official_season_baselines(
            shooter_id,season,captured_at,official_through_date,
            singles_targets,singles_hits,
            handicap_targets,handicap_hits,
            doubles_targets,doubles_hits,source
        )
        VALUES(?,?,CURRENT_TIMESTAMP,?,?,?,?,?,?,?,?)
        ON CONFLICT(shooter_id,season) DO UPDATE SET
            captured_at=CURRENT_TIMESTAMP,
            official_through_date=excluded.official_through_date,
            singles_targets=excluded.singles_targets,
            singles_hits=excluded.singles_hits,
            handicap_targets=excluded.handicap_targets,
            handicap_hits=excluded.handicap_hits,
            doubles_targets=excluded.doubles_targets,
            doubles_hits=excluded.doubles_hits,
            source=excluded.source
        """,
        (
            shooter_id,
            season,
            official_through_date,
            int(totals.singles_targets),
            int(totals.singles_hits),
            int(totals.handicap_targets),
            int(totals.handicap_hits),
            int(totals.doubles_targets),
            int(totals.doubles_hits),
            source,
        ),
    )


def get_baseline(database, shooter_id: int, season: int) -> dict:
    ensure_schema(database)
    rows = database.query(
        """
        SELECT * FROM official_season_baselines
        WHERE shooter_id=? AND season=?
        """,
        (shooter_id, season),
    )
    return dict(rows[0]) if rows else {}
