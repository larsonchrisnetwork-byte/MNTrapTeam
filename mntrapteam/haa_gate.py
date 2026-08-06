from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import csv


VALID_ZONES = {"CENTRAL", "NORTHERN", "SOUTHERN"}
VALID_ROUTES = {"ZONE", "STATE"}
VALID_COVERAGE = {"COMPLETE", "PARTIAL"}


@dataclass
class HAARecord:
    season: int
    shooter_id: int
    route: str
    shoot_name: str
    shoot_date: str
    shoot_zone: str
    resident_zone: str
    category: str
    singles_completed: bool
    handicap_completed: bool
    doubles_completed: bool
    source_url: str = ""
    source_label: str = ""
    source_coverage: str = "COMPLETE"
    verified: bool = True
    notes: str = ""

    @property
    def is_sub_junior(self) -> bool:
        value = self.category.upper().replace("-", "_").replace(" ", "_")
        return value in {"SUB_JR", "SUB_JUNIOR", "SUBJUNIOR"}

    @property
    def components_complete(self) -> bool:
        if self.is_sub_junior:
            return self.singles_completed and self.handicap_completed
        return (
            self.singles_completed
            and self.handicap_completed
            and self.doubles_completed
        )

    @property
    def route_matches(self) -> bool:
        route = self.route.upper()
        if route == "STATE":
            return True
        return (
            route == "ZONE"
            and self.shoot_zone.upper() in VALID_ZONES
            and self.shoot_zone.upper() == self.resident_zone.upper()
        )

    @property
    def qualifies(self) -> bool:
        return bool(self.verified and self.components_complete and self.route_matches)


def normalize_zone(value: str) -> str:
    zone = str(value or "").strip().upper()
    aliases = {
        "C": "CENTRAL",
        "N": "NORTHERN",
        "S": "SOUTHERN",
        "CENTRAL ZONE": "CENTRAL",
        "NORTHERN ZONE": "NORTHERN",
        "SOUTHERN ZONE": "SOUTHERN",
    }
    return aliases.get(zone, zone)


def normalize_route(value: str) -> str:
    route = str(value or "").strip().upper()
    aliases = {
        "MN STATE": "STATE",
        "MINNESOTA STATE": "STATE",
        "STATE SHOOT": "STATE",
        "RESIDENT ZONE": "ZONE",
        "ZONE SHOOT": "ZONE",
    }
    return aliases.get(route, route)


def ensure_schema(database) -> None:
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS haa_qualifications(
            id INTEGER PRIMARY KEY,
            season INTEGER NOT NULL,
            shooter_id INTEGER NOT NULL,
            route TEXT NOT NULL,
            shoot_name TEXT NOT NULL,
            shoot_date TEXT NOT NULL,
            shoot_zone TEXT NOT NULL DEFAULT '',
            resident_zone TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'MEN',
            singles_completed INTEGER NOT NULL DEFAULT 0,
            handicap_completed INTEGER NOT NULL DEFAULT 0,
            doubles_completed INTEGER NOT NULL DEFAULT 0,
            source_url TEXT NOT NULL DEFAULT '',
            source_label TEXT NOT NULL DEFAULT '',
            source_coverage TEXT NOT NULL DEFAULT 'COMPLETE',
            verified INTEGER NOT NULL DEFAULT 1,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(season, shooter_id, route, shoot_name)
        )
        """
    )


def save_record(database, record: HAARecord) -> None:
    ensure_schema(database)
    database.execute(
        """
        INSERT INTO haa_qualifications(
            season, shooter_id, route, shoot_name, shoot_date,
            shoot_zone, resident_zone, category,
            singles_completed, handicap_completed, doubles_completed,
            source_url, source_label, source_coverage, verified, notes
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(season, shooter_id, route, shoot_name)
        DO UPDATE SET
            shoot_date=excluded.shoot_date,
            shoot_zone=excluded.shoot_zone,
            resident_zone=excluded.resident_zone,
            category=excluded.category,
            singles_completed=excluded.singles_completed,
            handicap_completed=excluded.handicap_completed,
            doubles_completed=excluded.doubles_completed,
            source_url=excluded.source_url,
            source_label=excluded.source_label,
            source_coverage=excluded.source_coverage,
            verified=excluded.verified,
            notes=excluded.notes
        """,
        (
            record.season,
            record.shooter_id,
            normalize_route(record.route),
            record.shoot_name,
            record.shoot_date,
            normalize_zone(record.shoot_zone),
            normalize_zone(record.resident_zone),
            record.category,
            int(record.singles_completed),
            int(record.handicap_completed),
            int(record.doubles_completed),
            record.source_url,
            record.source_label,
            record.source_coverage.upper(),
            int(record.verified),
            record.notes,
        ),
    )


def records_for_shooter(database, season: int, shooter_id: int) -> list[HAARecord]:
    ensure_schema(database)
    rows = database.query(
        """
        SELECT * FROM haa_qualifications
        WHERE season=? AND shooter_id=?
        ORDER BY verified DESC, shoot_date, id
        """,
        (season, shooter_id),
    )
    return [
        HAARecord(
            season=row["season"],
            shooter_id=row["shooter_id"],
            route=row["route"],
            shoot_name=row["shoot_name"],
            shoot_date=row["shoot_date"],
            shoot_zone=row["shoot_zone"],
            resident_zone=row["resident_zone"],
            category=row["category"],
            singles_completed=bool(row["singles_completed"]),
            handicap_completed=bool(row["handicap_completed"]),
            doubles_completed=bool(row["doubles_completed"]),
            source_url=row["source_url"],
            source_label=row["source_label"],
            source_coverage=row["source_coverage"],
            verified=bool(row["verified"]),
            notes=row["notes"],
        )
        for row in rows
    ]


def haa_status(database, season: int, shooter_id: int) -> dict[str, Any]:
    records = records_for_shooter(database, season, shooter_id)
    qualifying = [record for record in records if record.qualifies]
    best = qualifying[0] if qualifying else (records[0] if records else None)

    if best is None:
        return {
            "haa_qualified": False,
            "haa_gate": "NOT COMPLETED",
            "haa_route": "",
            "haa_reason": "No verified qualifying HAA record",
            "source_coverage": "",
            "records": [],
        }

    reason = ""
    if not best.verified:
        reason = "HAA record is not verified"
    elif not best.components_complete:
        reason = "Required HAA components were not all completed"
    elif not best.route_matches:
        reason = "Zone HAA does not match the shooter’s resident Minnesota zone"

    return {
        "haa_qualified": bool(qualifying),
        "haa_gate": "QUALIFIED" if qualifying else "NOT COMPLETED",
        "haa_route": best.route,
        "haa_reason": "" if qualifying else reason,
        "source_coverage": best.source_coverage,
        "record": asdict(best),
        "records": [asdict(record) for record in records],
    }


def rebuild_season_haa_flags(database, season: int) -> int:
    """Write the registry's qualification result into season_stats.haa_complete."""
    ensure_schema(database)
    rows = database.query(
        "SELECT shooter_id FROM season_stats WHERE season=?",
        (season,),
    )
    updated = 0
    for row in rows:
        status = haa_status(database, season, row["shooter_id"])
        database.execute(
            """
            UPDATE season_stats
            SET haa_complete=?
            WHERE season=? AND shooter_id=?
            """,
            (int(status["haa_qualified"]), season, row["shooter_id"]),
        )
        updated += 1
    return updated


def active_team_pool(database, team_service, season: int, team: str) -> dict[str, Any]:
    rankings = team_service.rankings(season, team)
    active = []
    inactive = []

    for row in rankings:
        status = haa_status(database, season, row["id"])
        item = dict(row)
        item.update(status)
        if status["haa_qualified"]:
            active.append(item)
        else:
            item["selected"] = False
            inactive.append(item)

    # HAA-gated cut line: only shooters inside the mandatory gate can set it.
    eligible_active = [row for row in active if row.get("eligible")]
    size = int(team_service.rules.rules["teams"][team]["size"])
    selected = eligible_active[:size]
    cut_line = selected[-1]["hoa"] if len(selected) == size else None

    for index, row in enumerate(active, 1):
        row["haa_pool_rank"] = index
        row["selected"] = bool(row in selected)
        row["haa_cut_line_hoa"] = cut_line
        row["haa_gap_to_cut"] = (
            row["hoa"] - cut_line if cut_line is not None else None
        )

    return {
        "team": team,
        "team_size": size,
        "active": active,
        "inactive": inactive,
        "qualified_count": len(active),
        "selected_count": len(selected),
        "cut_line_hoa": cut_line,
    }


def _truth(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "yes", "true", "y", "complete"}


def import_registry_csv(database, path: Path, season: int) -> dict[str, Any]:
    """Import a reviewed HAA participant registry.

    ATA number is preferred. Name matching is exact-normalized only; ambiguous
    names are reported rather than silently attached to the wrong shooter.
    """
    ensure_schema(database)
    imported = 0
    created = 0
    warnings: list[str] = []

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    for line_number, row in enumerate(rows, 2):
        ata = "".join(ch for ch in str(row.get("ata_number") or "") if ch.isdigit())
        name = " ".join(str(row.get("name") or "").split())
        if not name:
            warnings.append(f"Row {line_number}: missing shooter name")
            continue

        shooter_rows = []
        if ata:
            shooter_rows = database.query(
                "SELECT id FROM shooters WHERE ata_number=?",
                (ata,),
            )
        if not shooter_rows:
            shooter_rows = database.query(
                "SELECT id FROM shooters WHERE lower(trim(display_name))=lower(trim(?))",
                (name,),
            )
        if len(shooter_rows) > 1:
            warnings.append(f"Row {line_number}: ambiguous shooter name {name}")
            continue
        if not shooter_rows:
            shooter_id = database.upsert_shooter(
                ata,
                name,
                row.get("category") or "MEN",
                "MN",
            )
            created += 1
        else:
            shooter_id = shooter_rows[0]["id"]

        route = normalize_route(row.get("route") or "")
        shoot_zone = normalize_zone(row.get("shoot_zone") or "")
        resident_zone = normalize_zone(row.get("resident_zone") or "")
        coverage = str(row.get("source_coverage") or "COMPLETE").upper()
        if route not in VALID_ROUTES:
            warnings.append(f"Row {line_number}: invalid route {route!r}")
            continue
        if route == "ZONE" and shoot_zone not in VALID_ZONES:
            warnings.append(f"Row {line_number}: invalid shoot zone {shoot_zone!r}")
            continue
        if coverage not in VALID_COVERAGE:
            warnings.append(f"Row {line_number}: invalid source coverage {coverage!r}")
            continue

        record = HAARecord(
            season=season,
            shooter_id=shooter_id,
            route=route,
            shoot_name=row.get("shoot_name") or "",
            shoot_date=row.get("shoot_date") or "",
            shoot_zone=shoot_zone,
            resident_zone=resident_zone,
            category=row.get("category") or "MEN",
            singles_completed=_truth(row.get("singles_completed")),
            handicap_completed=_truth(row.get("handicap_completed")),
            doubles_completed=_truth(row.get("doubles_completed")),
            source_url=row.get("source_url") or "",
            source_label=row.get("source_label") or "",
            source_coverage=coverage,
            verified=_truth(row.get("verified", "yes")),
            notes=row.get("notes") or "",
        )
        save_record(database, record)
        imported += 1

    rebuild_season_haa_flags(database, season)
    return {
        "rows_read": len(rows),
        "rows_imported": imported,
        "shooters_created": created,
        "warnings": warnings,
    }
