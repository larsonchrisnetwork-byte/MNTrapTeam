from __future__ import annotations

import json
from pathlib import Path

from .database import Database
from .identity import normalize_ata
from .paths import DATA


ROOT = Path(__file__).resolve().parents[1]
ZONE_CONFIG = ROOT / "config" / "mta_zone_counties.json"
CITY_CONFIG = ROOT / "config" / "mn_city_county_overrides.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_city(city: str) -> str:
    value = " ".join(str(city or "").strip().upper().split())
    aliases = {
        "GLENCO": "GLENCOE",
    }
    return aliases.get(value, value)


def _load_residences():
    path = (
        DATA
        / "connector_downloads"
        / "zone_residence"
        / "southern_2026_residences.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"Residence file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return path, data.get("captured") or []


def _county_to_zone(county: str, zones: dict) -> str:
    for zone, counties in zones.items():
        if county in counties:
            return zone
    return "UNKNOWN"


def classify():
    source_path, captured = _load_residences()
    zones = _load_json(ZONE_CONFIG)
    city_map = _load_json(CITY_CONFIG)

    rows = []

    for item in captured:
        ata = normalize_ata(item.get("ata"))
        raw_city = str(item.get("city") or "").strip()
        city = _normalize_city(raw_city)
        state = str(item.get("state") or "").strip().upper()

        county_value = city_map.get(city)

        if isinstance(county_value, list):
            county = " / ".join(county_value)
            zone = "AMBIGUOUS"
        elif isinstance(county_value, str):
            county = county_value
            zone = _county_to_zone(county, zones)
        else:
            county = "UNKNOWN"
            zone = "UNKNOWN"

        rows.append({
            "ata": ata,
            "name": str(item.get("name") or "").strip(),
            "raw_city": raw_city,
            "city": city,
            "state": state,
            "county": county,
            "zone": zone,
        })

    return source_path, rows


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


def _find_shooter(db, ata):
    rows = [
        dict(r)
        for r in db.query(
            """
            SELECT id, ata_number, display_name
            FROM shooters
            WHERE ata_number=?
            """,
            (ata,),
        )
    ]
    return rows[0] if len(rows) == 1 else None


def preview() -> int:
    source_path, rows = classify()

    southern = [r for r in rows if r["zone"] == "Southern"]
    other = [r for r in rows if r["zone"] in {"Central", "Northern"}]
    ambiguous = [r for r in rows if r["zone"] == "AMBIGUOUS"]
    unknown = [r for r in rows if r["zone"] == "UNKNOWN"]

    print("MNTrapTeam Southern Zone Residence Classification")
    print("=================================================")
    print(f"Residence source: {source_path}")
    print(f"Zone config: {ZONE_CONFIG}")
    print()

    print("SOUTHERN — HOME-ZONE HAA ELIGIBLE")
    print("---------------------------------")
    for row in southern:
        print(
            f"{row['ata']} | {row['name']} | {row['city']}, {row['state']} | "
            f"{row['county']} County | SOUTHERN"
        )

    print()
    print("NOT SOUTHERN")
    print("------------")
    for row in other:
        print(
            f"{row['ata']} | {row['name']} | {row['city']}, {row['state']} | "
            f"{row['county']} County | {row['zone'].upper()}"
        )

    print()
    print("AMBIGUOUS / MANUAL REVIEW")
    print("-------------------------")
    if ambiguous:
        for row in ambiguous:
            print(
                f"{row['ata']} | {row['name']} | {row['city']}, {row['state']} | "
                f"{row['county']} | AMBIGUOUS"
            )
    else:
        print("None")

    print()
    print("UNKNOWN")
    print("-------")
    if unknown:
        for row in unknown:
            print(
                f"{row['ata']} | {row['name']} | "
                f"{row['city']}, {row['state']}"
            )
    else:
        print("None")

    print()
    print("SUMMARY")
    print("-------")
    print(f"Southern: {len(southern)}")
    print(f"Other zones: {len(other)}")
    print(f"Ambiguous: {len(ambiguous)}")
    print(f"Unknown: {len(unknown)}")
    return 0


def write_verified() -> int:
    db = Database(DATA / "mntrapteam.db")
    _ensure_tables(db)
    _source_path, rows = classify()

    southern = [r for r in rows if r["zone"] == "Southern"]

    written = 0
    skipped = 0

    print("MNTrapTeam Southern Zone HAA Verified Import")
    print("===========================================")
    print()

    for row in southern:
        shooter = _find_shooter(db, row["ata"])

        if shooter is None:
            print(
                f"{row['ata']} | {row['name']} | SKIPPED: "
                f"ATA-numbered shooter record not found uniquely"
            )
            skipped += 1
            continue

        shooter_id = int(shooter["id"])

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
                row["city"],
                row["state"],
                "Southern",
                "MyATA Search/Buddies residence + configured MTA county-zone map",
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
            VALUES(?,?,?,?,200,100,100,?,?,1,1,1,?,CURRENT_TIMESTAMP)
            ON CONFLICT(shooter_id,season,zone) DO UPDATE SET
                shoot_name=excluded.shoot_name,
                singles_targets=200,
                handicap_targets=100,
                doubles_targets=100,
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
                "Southern",
                "2026 MTA Southern Zone - Lester Prairie",
                row["city"],
                row["state"],
                "SOS shoot 5220 full 3-event HAA completion + MyATA residence + MTA zone config",
            ),
        )

        print(
            f"{row['ata']} | {shooter['display_name']} | "
            f"{row['city']} | {row['county']} County | VERIFIED SOUTHERN HAA"
        )
        written += 1

    print()
    print(f"Southern Zone HAA records written: {written}")
    print(f"Skipped: {skipped}")
    return 0 if written else 2


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("preview", "write"),
        nargs="?",
        default="preview",
    )
    args = parser.parse_args()
    raise SystemExit(preview() if args.action == "preview" else write_verified())
