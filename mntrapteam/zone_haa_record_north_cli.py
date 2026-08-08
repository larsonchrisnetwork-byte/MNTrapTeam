from __future__ import annotations

from .database import Database
from .identity import normalize_ata
from .paths import DATA


NORTHERN_VERIFIED = (
    {
        "ata": "1776550",
        "name": "Craig Isaacson",
        "city": "ST MICHAEL",
        "state": "MN",
        "zone": "Northern",
    },
    {
        "ata": "0416492",
        "name": "Russ Hiltz",
        "city": "BEMIDJI",
        "state": "MN",
        "zone": "Northern",
    },
    {
        "ata": "2805615",
        "name": "Troy Haverly",
        "city": "NEW LONDON",
        "state": "MN",
        "zone": "Northern",
    },
)


EVENTS = {
    "singles": ("N ZONE CHAMPIONSHIP SINGLES", 200),
    "handicap": ("N ZONE CHAMPIONSHIP HANDICAP", 100),
    "doubles": ("N ZONE CHAMPIONSHIP DOUBLES", 100),
}


def _rows(db, sql, params=()):
    return [dict(r) for r in db.query(sql, params)]


def _ensure_tables(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS shooter_zone_residence (
            shooter_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            home_zone TEXT NOT NULL,
            source TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (shooter_id, season)
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS zone_haa_qualifications (
            shooter_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            zone TEXT NOT NULL,
            shoot_name TEXT NOT NULL,
            singles_targets INTEGER NOT NULL DEFAULT 0,
            handicap_targets INTEGER NOT NULL DEFAULT 0,
            doubles_targets INTEGER NOT NULL DEFAULT 0,
            residence_city TEXT,
            residence_state TEXT,
            residence_verified INTEGER NOT NULL DEFAULT 0,
            event_complete INTEGER NOT NULL DEFAULT 0,
            verified INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (shooter_id, season, zone)
        )
        """
    )


def _shooter(db, ata):
    rows = _rows(
        db,
        """
        SELECT id, ata_number, display_name
        FROM shooters
        WHERE ata_number=?
        """,
        (ata,),
    )
    if len(rows) != 1:
        raise RuntimeError(
            f"Expected one shooter for ATA {ata}; found {len(rows)}"
        )
    return rows[0]


def _event_targets(db, shooter_id, event_name):
    rows = _rows(
        db,
        """
        SELECT COALESCE(SUM(targets),0) AS targets
        FROM scores
        WHERE shooter_id=?
          AND upper(COALESCE(event_name,''))=?
        """,
        (shooter_id, event_name.upper()),
    )
    return int(rows[0]["targets"] or 0) if rows else 0


def main() -> int:
    db = Database(DATA / "mntrapteam.db")
    _ensure_tables(db)

    print("MNTrapTeam Northern Zone HAA Verification Import")
    print("===============================================")
    print()

    written = 0

    for item in NORTHERN_VERIFIED:
        ata = normalize_ata(item["ata"])
        shooter = _shooter(db, ata)
        shooter_id = int(shooter["id"])

        singles = _event_targets(
            db, shooter_id, EVENTS["singles"][0]
        )
        handicap = _event_targets(
            db, shooter_id, EVENTS["handicap"][0]
        )
        doubles = _event_targets(
            db, shooter_id, EVENTS["doubles"][0]
        )

        event_complete = int(
            singles >= EVENTS["singles"][1]
            and handicap >= EVENTS["handicap"][1]
            and doubles >= EVENTS["doubles"][1]
        )

        residence_verified = int(
            item["state"] == "MN"
            and item["zone"] == "Northern"
        )

        verified = int(
            event_complete
            and residence_verified
        )

        print(
            f"{ata} | {shooter['display_name']} | "
            f"{item['city']}, {item['state']} | "
            f"S {singles} H {handicap} D {doubles} | "
            f"verified={'YES' if verified else 'NO'}"
        )

        if not verified:
            print("  NOT WRITTEN: evidence is incomplete.")
            continue

        db.execute(
            """
            INSERT INTO shooter_zone_residence(
                shooter_id, season, city, state, home_zone,
                source, verified, updated_at
            )
            VALUES(?,?,?,?,?,?,1,CURRENT_TIMESTAMP)
            ON CONFLICT(shooter_id,season) DO UPDATE SET
                city=excluded.city,
                state=excluded.state,
                home_zone=excluded.home_zone,
                source=excluded.source,
                verified=1,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                shooter_id,
                2026,
                item["city"],
                item["state"],
                item["zone"],
                "MyATA Search/Buddies pre-selection residence",
            ),
        )

        db.execute(
            """
            INSERT INTO zone_haa_qualifications(
                shooter_id, season, zone, shoot_name,
                singles_targets, handicap_targets, doubles_targets,
                residence_city, residence_state,
                residence_verified, event_complete, verified,
                source, updated_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,1,1,1,?,CURRENT_TIMESTAMP)
            ON CONFLICT(shooter_id,season,zone) DO UPDATE SET
                shoot_name=excluded.shoot_name,
                singles_targets=excluded.singles_targets,
                handicap_targets=excluded.handicap_targets,
                doubles_targets=excluded.doubles_targets,
                residence_city=excluded.residence_city,
                residence_state=excluded.residence_state,
                residence_verified=1,
                event_complete=1,
                verified=1,
                source=excluded.source,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                shooter_id,
                2026,
                "Northern",
                "2026 MTA Northern Zone Shoot",
                singles,
                handicap,
                doubles,
                item["city"],
                item["state"],
                "ShootScoreBoard event scores + MyATA residence + MTA zone map",
            ),
        )

        written += 1

    print()
    print(f"Verified Northern Zone HAA records written: {written}")
    print()
    print(
        "These records are stored separately from State HAA qualifications. "
        "Live Team gate integration will use STATE HAA OR verified HOME-ZONE HAA."
    )

    return 0 if written else 2


if __name__ == "__main__":
    raise SystemExit(main())
