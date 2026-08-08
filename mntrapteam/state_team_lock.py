from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import DATA
from .rules import RulesEngine


def ensure_schema(database) -> None:
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS state_team_qualification_lock(
            shooter_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            haa_route TEXT NOT NULL,
            qualifying_event TEXT NOT NULL,
            qualifying_date TEXT NOT NULL DEFAULT '',
            qualifying_category TEXT NOT NULL,
            state_team TEXT NOT NULL,
            zone TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 1,
            locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(shooter_id, season)
        )
        """
    )


def normalize_qualifying_category(value: Any) -> str:
    c = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "": "MEN",
        "M": "MEN",
        "L": "LADY",
        "L1": "L1",
        "L2": "L2",
        "LADY": "LADY",
        "LADY_I": "L1",
        "LADY_II": "L2",
        "SBV": "SBV",
        "SUBVET": "SBV",
        "SUB_VET": "SBV",
        "SUB_VETERAN": "SBV",
        "V": "VET",
        "VT": "VET",
        "VET": "VET",
        "VETERAN": "VET",
        "SRV": "SR_VET",
        "SRVT": "SR_VET",
        "SR_VET": "SR_VET",
        "SENIOR_VET": "SR_VET",
        "J": "JUNIOR",
        "JR": "JUNIOR",
        "JUNIOR": "JUNIOR",
        "JG": "JUNIOR_GOLD",
        "JUNIOR_GOLD": "JUNIOR_GOLD",
        "SJ": "SUB_JR",
        "SUB_JR": "SUB_JR",
        "SUB_JUNIOR": "SUB_JR",
    }
    return aliases.get(c, c or "MEN")


def _latest_southern_report() -> Path | None:
    root = DATA / "connector_downloads" / "sos_zone"
    if not root.exists():
        return None
    captures = sorted(
        root.glob("southern_5220_*/005_shootHighGunReport.json"),
        key=lambda p: p.stat().st_mtime,
    )
    return captures[-1] if captures else None


def _southern_categories() -> dict[str, str]:
    path = _latest_southern_report()
    if path is None:
        return {}

    document = json.loads(path.read_text(encoding="utf-8"))
    rows = (
        document.get("data", {})
        .get("payload", {})
        .get("sortedReportData", [])
    )

    result = {}
    for row in rows:
        ata = "".join(ch for ch in str(row.get("ataId") or "") if ch.isdigit())
        if ata:
            result[ata] = normalize_qualifying_category(row.get("category"))
    return result


def _state_records(database, season: int) -> dict[int, dict]:
    rows = database.query(
        """
        SELECT h.*, s.ata_number, s.display_name
        FROM haa_qualifications h
        JOIN shooters s ON s.id=h.shooter_id
        WHERE h.season=?
          AND h.verified=1
          AND upper(h.route)='STATE'
        ORDER BY h.shooter_id, h.shoot_date, h.id
        """,
        (season,),
    )

    result = {}
    for raw in rows:
        row = dict(raw)
        category = normalize_qualifying_category(row.get("category"))
        sub_jr = category == "SUB_JR"
        complete = (
            bool(row.get("singles_completed"))
            and bool(row.get("handicap_completed"))
            and (sub_jr or bool(row.get("doubles_completed")))
        )
        if complete:
            result.setdefault(int(row["shooter_id"]), row)
    return result


def build_locks(database, season: int = 2026) -> list[dict]:
    rules = RulesEngine()
    state = _state_records(database, season)
    southern_categories = _southern_categories()

    zone_rows = database.query(
        """
        SELECT z.*, s.ata_number, s.display_name, s.category AS shooter_category
        FROM zone_haa_qualifications z
        JOIN shooters s ON s.id=z.shooter_id
        WHERE z.season=?
          AND z.verified=1
          AND z.event_complete=1
          AND z.residence_verified=1
        ORDER BY z.shooter_id
        """,
        (season,),
    )
    zone = {int(r["shooter_id"]): dict(r) for r in zone_rows}

    locks = []
    for shooter_id in sorted(set(state) | set(zone)):
        if shooter_id in zone:
            row = zone[shooter_id]
            zone_name = str(row.get("zone") or "").upper()
            ata = "".join(ch for ch in str(row.get("ata_number") or "") if ch.isdigit())

            category = None
            category_source = ""
            if zone_name == "SOUTHERN":
                category = southern_categories.get(ata)
                category_source = "SOS Southern Zone full report"

            if not category and shooter_id in state:
                category = normalize_qualifying_category(state[shooter_id].get("category"))
                category_source = "same-season verified State HAA category fallback"

            if not category:
                category = normalize_qualifying_category(row.get("shooter_category"))
                category_source = "event-imported shooter category fallback"

            locks.append(
                {
                    "shooter_id": shooter_id,
                    "ata_number": ata,
                    "display_name": row.get("display_name") or "",
                    "haa_route": "ZONE",
                    "qualifying_event": row.get("shoot_name") or f"{zone_name.title()} Zone",
                    "qualifying_date": "",
                    "qualifying_category": category,
                    "state_team": rules.team_for_category(category),
                    "zone": zone_name,
                    "source": f"verified home-zone HAA; category from {category_source}",
                }
            )
        else:
            row = state[shooter_id]
            category = normalize_qualifying_category(row.get("category"))
            locks.append(
                {
                    "shooter_id": shooter_id,
                    "ata_number": "".join(
                        ch for ch in str(row.get("ata_number") or "") if ch.isdigit()
                    ),
                    "display_name": row.get("display_name") or "",
                    "haa_route": "STATE",
                    "qualifying_event": row.get("shoot_name") or "MN State Shoot",
                    "qualifying_date": row.get("shoot_date") or "",
                    "qualifying_category": category,
                    "state_team": rules.team_for_category(category),
                    "zone": "",
                    "source": "verified MN State HAA qualifying record",
                }
            )
    return locks


def write_locks(database, season: int = 2026) -> list[dict]:
    ensure_schema(database)
    locks = build_locks(database, season)

    # The State Shoot has closed the HAA gate. These fields become the frozen
    # candidate-pool flags used by the existing State Team ranking engine.
    database.execute(
        """
        UPDATE season_stats
        SET haa_complete=0,
            category_declared=NULL
        WHERE season=?
        """,
        (season,),
    )
    database.execute(
        "DELETE FROM state_team_qualification_lock WHERE season=?",
        (season,),
    )

    for item in locks:
        database.execute(
            """
            INSERT INTO state_team_qualification_lock(
                shooter_id,season,haa_route,qualifying_event,
                qualifying_date,qualifying_category,state_team,zone,
                source,verified,locked_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,1,CURRENT_TIMESTAMP)
            """,
            (
                item["shooter_id"], season, item["haa_route"],
                item["qualifying_event"], item["qualifying_date"],
                item["qualifying_category"], item["state_team"],
                item["zone"], item["source"],
            ),
        )
        database.execute(
            """
            UPDATE season_stats
            SET haa_complete=1,
                category_declared=?
            WHERE shooter_id=? AND season=?
            """,
            (item["qualifying_category"], item["shooter_id"], season),
        )

    return locks
