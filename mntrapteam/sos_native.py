from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import re

from .haa_gate import HAARecord, rebuild_season_haa_flags, save_record
from .matcher import ShooterMatcher
from .normalization import normalize_event_date, normalize_shoot_name
from .reconciliation import ensure_schema
from .source_adapters import observe_event
from .zone_residency import get_resident_zone


SOS_API = "https://api-dot-sosclays-app.appspot.com/1"

ZONE_HINTS = {
    "SOUTHERN": ("SOUTHERN ZONE", "LESTER PRAIRIE"),
    "CENTRAL": ("CENTRAL ZONE", "BEAVERBROOK"),
    "NORTHERN": ("NORTHERN ZONE", "GRAND RAPIDS"),
}

STATE_HINTS = (
    "MINNESOTA STATE SHOOT",
    "MN STATE SHOOT",
)

HAA_TARGETS = {
    "singles": 200,
    "handicap": 100,
    "doubles": 100,
}


@dataclass
class SOSShoot:
    shoot_id: int
    name: str
    start_date: str
    end_date: str
    locations: list[Any]


@dataclass
class SOSSyncResult:
    shoot_id: int
    shoot_name: str
    observations_written: int
    shooters_created: int
    haa_records_written: int
    warnings: list[str]


def _upper(value: Any) -> str:
    return " ".join(str(value or "").upper().split())


def classify_shoot(name: str) -> tuple[str, str]:
    upper = _upper(name)

    if any(hint in upper for hint in STATE_HINTS):
        return ("STATE", "")

    for zone, hints in ZONE_HINTS.items():
        if any(hint in upper for hint in hints):
            return ("ZONE", zone)

    return ("", "")


def _extract_payload(response: dict[str, Any]) -> Any:
    if not isinstance(response, dict):
        raise ValueError("SOS response must be an object")
    if not response.get("success", False):
        raise ValueError("SOS response reported success=false")
    return response.get("payload")


def load_capture_json(capture_dir: Path, filename: str) -> Any:
    return json.loads(
        (Path(capture_dir) / filename).read_text(encoding="utf-8")
    )


def shoots_from_list_payload(payload: Any) -> list[SOSShoot]:
    rows = payload if isinstance(payload, list) else []
    result = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        shoot_id = row.get("shootId")
        name = str(row.get("name") or "").strip()
        if shoot_id in (None, "") or not name:
            continue

        result.append(
            SOSShoot(
                shoot_id=int(shoot_id),
                name=name,
                start_date=normalize_event_date(str(row.get("startDate") or "")),
                end_date=normalize_event_date(str(row.get("endDate") or "")),
                locations=list(row.get("locations") or []),
            )
        )

    return result


def find_minnesota_haa_shoots(shoots: list[SOSShoot], season: int) -> list[SOSShoot]:
    found: dict[tuple[str, str], SOSShoot] = {}

    for shoot in shoots:
        if not shoot.start_date.startswith(f"{season}-"):
            continue
        route, zone = classify_shoot(shoot.name)
        if not route:
            continue
        found.setdefault((route, zone), shoot)

    order = [
        ("ZONE", "SOUTHERN"),
        ("ZONE", "CENTRAL"),
        ("ZONE", "NORTHERN"),
        ("STATE", ""),
    ]
    return [found[key] for key in order if key in found]


def _flatten_report_rows(report_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(report_payload, dict):
        return []

    data = report_payload.get("sortedReportData")
    if isinstance(data, list):
        flattened = []
        for item in data:
            if isinstance(item, dict):
                flattened.append(item)
                for key in (
                    "shooters",
                    "rows",
                    "members",
                    "participants",
                    "reportData",
                    "data",
                ):
                    value = item.get(key)
                    if isinstance(value, list):
                        flattened.extend(
                            row for row in value if isinstance(row, dict)
                        )
        return flattened

    if isinstance(data, dict):
        flattened = []
        for value in data.values():
            if isinstance(value, list):
                flattened.extend(
                    row for row in value if isinstance(row, dict)
                )
            elif isinstance(value, dict):
                flattened.append(value)
        return flattened

    return []


def _first(row: dict[str, Any], *names: str, default=None):
    lowered = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name.lower() in lowered:
            value = lowered[name.lower()]
            if value not in (None, ""):
                return value
    return default


def _int(row: dict[str, Any], *names: str) -> int:
    value = _first(row, *names, default=0)
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _name(row: dict[str, Any]) -> str:
    direct = _first(
        row,
        "name",
        "shooterName",
        "memberName",
        "displayName",
        "fullName",
    )
    if direct:
        return " ".join(str(direct).split())

    first = _first(row, "firstName", default="")
    last = _first(row, "lastName", default="")
    return " ".join(f"{first} {last}".split())


def _ata(row: dict[str, Any]) -> str:
    value = _first(
        row,
        "ataId",
        "ataNumber",
        "ata",
        "memberNumber",
        default="",
    )
    return "".join(character for character in str(value) if character.isdigit())


def _category(row: dict[str, Any]) -> str:
    value = _upper(
        _first(
            row,
            "category",
            "specialCategory",
            "categoryCode",
            default="",
        )
    )
    aliases = {
        "": "MEN",
        "JR": "JUNIOR",
        "JRG": "JUNIOR_GOLD",
        "SJ": "SUB_JR",
        "SUBJ": "SUB_JR",
        "SUB-JR": "SUB_JR",
        "SUBV": "SUB_VET",
        "VT": "VET",
        "SRVT": "SR_VET",
        "LD1": "LADY_I",
        "LD2": "LADY_II",
    }
    return aliases.get(value, value or "MEN")


def _state(row: dict[str, Any]) -> str:
    return _upper(
        _first(
            row,
            "state",
            "stateProvince",
            "residentState",
            default="",
        )
    )


def _discipline_values(row: dict[str, Any]) -> dict[str, tuple[int, int]]:
    mappings = {
        "singles": (
            ("singlesTargets", "singlesShot", "singlesTargetCount"),
            ("singlesHits", "singlesScore", "singlesTotal"),
        ),
        "handicap": (
            ("handicapTargets", "handicapShot", "handicapTargetCount"),
            ("handicapHits", "handicapScore", "handicapTotal"),
        ),
        "doubles": (
            ("doublesTargets", "doublesShot", "doublesTargetCount"),
            ("doublesHits", "doublesScore", "doublesTotal"),
        ),
    }

    result = {}
    for discipline, (target_names, hit_names) in mappings.items():
        targets = _int(row, *target_names)
        hits = _int(row, *hit_names)
        if targets:
            result[discipline] = (targets, hits)

    return result


def _shooter_id(
    database,
    matcher: ShooterMatcher,
    row: dict[str, Any],
) -> tuple[int | None, bool]:
    ata = _ata(row)
    name = _name(row)

    if ata:
        matches = database.query(
            "SELECT id FROM shooters WHERE ata_number=?",
            (ata,),
        )
        if matches:
            return int(matches[0]["id"]), False

    shooter_id, _confidence = matcher.match(name, ata)
    if shooter_id is not None:
        return int(shooter_id), False

    if not name:
        return None, False

    shooter_id = database.upsert_shooter(
        ata,
        name,
        _category(row),
        "MN" if _state(row) == "MN" else _state(row),
    )
    return int(shooter_id), True


def import_report_payload(
    database,
    shoot: SOSShoot,
    report_payload: Any,
    season: int,
) -> SOSSyncResult:
    ensure_schema(database)
    matcher = ShooterMatcher(database, 88)
    rows = _flatten_report_rows(report_payload)

    route, zone = classify_shoot(shoot.name)
    observations = 0
    created = 0
    haa_records = 0
    warnings: list[str] = []

    haa_progress: dict[int, dict[str, Any]] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue

        if _state(row) not in {"", "MN"}:
            continue

        shooter_id, was_created = _shooter_id(database, matcher, row)
        if shooter_id is None:
            continue

        if was_created:
            created += 1

        category = _category(row)
        disciplines = _discipline_values(row)

        if not disciplines:
            continue

        for discipline, (targets, hits) in disciplines.items():
            observe_event(
                database,
                shooter_id=shooter_id,
                season=season,
                event_date=shoot.end_date or shoot.start_date,
                shoot_name=normalize_shoot_name(shoot.name),
                discipline=discipline,
                targets=targets,
                hits=hits,
                source="sosclays",
                source_record_id=(
                    f"sos:{shoot.shoot_id}:{shooter_id}:{discipline}"
                ),
                club=normalize_shoot_name(shoot.name),
                state="MN",
                in_state=True,
                official=False,
            )
            observations += 1

        if route:
            item = haa_progress.setdefault(
                shooter_id,
                {
                    "category": category,
                    "singles": 0,
                    "handicap": 0,
                    "doubles": 0,
                },
            )
            for discipline, (targets, _hits) in disciplines.items():
                item[discipline] += targets

    for shooter_id, item in haa_progress.items():
        is_sub_jr = item["category"] in {"SUB_JR", "SUB_JUNIOR"}
        complete = (
            item["singles"] >= 200
            and item["handicap"] >= 100
            and (is_sub_jr or item["doubles"] >= 100)
        )

        if not complete:
            continue

        resident_zone = ""
        verified = route == "STATE"

        if route == "ZONE":
            resident = get_resident_zone(database, shooter_id, season)
            resident_zone = resident["resident_zone"]
            verified = (
                bool(resident["verified"])
                and resident_zone == zone
            )

        save_record(
            database,
            HAARecord(
                season=season,
                shooter_id=shooter_id,
                route=route,
                shoot_name=shoot.name,
                shoot_date=shoot.end_date or shoot.start_date,
                shoot_zone=zone,
                resident_zone=resident_zone,
                category=item["category"],
                singles_completed=item["singles"] >= 200,
                handicap_completed=item["handicap"] >= 100,
                doubles_completed=item["doubles"] >= 100,
                source_url=f"SOS shoot {shoot.shoot_id}",
                source_label="SOS Clays live JSON",
                source_coverage="COMPLETE",
                verified=verified,
                notes=(
                    "Live SOS HAA qualification."
                    if verified
                    else (
                        "Zone HAA complete; resident-zone verification pending "
                        "or zone does not match verified residence."
                    )
                ),
            ),
        )
        haa_records += 1

    rebuild_season_haa_flags(database, season)

    if not rows:
        warnings.append(
            "No shooter rows recognized in sortedReportData. "
            "Capture one full shootHighGunReport JSON for parser refinement."
        )

    return SOSSyncResult(
        shoot_id=shoot.shoot_id,
        shoot_name=shoot.name,
        observations_written=observations,
        shooters_created=created,
        haa_records_written=haa_records,
        warnings=warnings,
    )
