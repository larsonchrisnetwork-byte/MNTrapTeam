from __future__ import annotations

from .haa_gate import normalize_zone, VALID_ZONES


def ensure_resident_zone_schema(database) -> None:
    database.execute(
        '''
        CREATE TABLE IF NOT EXISTS shooter_resident_zones(
            shooter_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            resident_zone TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            verified INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(shooter_id, season),
            FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE
        )
        '''
    )


def set_resident_zone(database, shooter_id, season, zone, *, source, verified):
    ensure_resident_zone_schema(database)
    normalized = normalize_zone(zone)
    if normalized not in VALID_ZONES:
        raise ValueError(f"Invalid Minnesota resident zone: {zone!r}")
    database.execute(
        '''
        INSERT INTO shooter_resident_zones(
            shooter_id,season,resident_zone,source,verified,updated_at
        ) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(shooter_id,season) DO UPDATE SET
            resident_zone=excluded.resident_zone,
            source=excluded.source,
            verified=excluded.verified,
            updated_at=CURRENT_TIMESTAMP
        ''',
        (shooter_id, season, normalized, source, int(verified)),
    )


def get_resident_zone(database, shooter_id, season):
    ensure_resident_zone_schema(database)
    rows = database.query(
        '''
        SELECT resident_zone,source,verified
        FROM shooter_resident_zones
        WHERE shooter_id=? AND season=?
        ''',
        (shooter_id, season),
    )
    if not rows:
        return {"resident_zone": "", "source": "", "verified": False}
    row = rows[0]
    return {
        "resident_zone": normalize_zone(row["resident_zone"]),
        "source": row["source"],
        "verified": bool(row["verified"]),
    }
