from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import re

from .database import Database
from .haa_gate import HAARecord, rebuild_season_haa_flags, save_record
from .paths import DATA


STATE_HAA_EVENT_COUNT = 3
STATE_HAA_TARGETS = 400


@dataclass
class StateHAAImportResult:
    shoot_id: int
    report_rows: int
    minnesota_rows: int
    haa_completers: int
    shooter_matches: int
    shooter_creates: int
    haa_records_written: int


def _name(row: dict[str, Any]) -> str:
    return " ".join(
        str(value or "").strip()
        for value in (
            row.get("firstName"),
            row.get("middleName"),
            row.get("lastName"),
        )
        if str(value or "").strip()
    )


def _ata(row: dict[str, Any]) -> str:
    return "".join(
        character
        for character in str(row.get("ataId") or "")
        if character.isdigit()
    )


def _category(row: dict[str, Any]) -> str:
    value = str(row.get("category") or "").strip().upper()
    aliases = {
        "": "MEN",
        "J": "JUNIOR",
        "JR": "JUNIOR",
        "JG": "JUNIOR_GOLD",
        "JRG": "JUNIOR_GOLD",
        "SJ": "SUB_JR",
        "SV": "SUB_VET",
        "SUBV": "SUB_VET",
        "V": "VET",
        "VT": "VET",
        "SRV": "SR_VET",
        "SRVT": "SR_VET",
        "LI": "LADY_I",
        "LII": "LADY_II",
        "LD1": "LADY_I",
        "LD2": "LADY_II",
    }
    return aliases.get(value, value or "MEN")


def _payload(path: Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not raw.get("success", False):
        raise ValueError("SOS report success=false")
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("SOS report payload is not an object")
    return payload


def validate_state_haa_report(payload: dict[str, Any]) -> None:
    events = payload.get("eventsData")
    if not isinstance(events, list):
        raise ValueError("SOS State report has no eventsData list")

    haa_events = [
        event for event in events
        if isinstance(event, dict) and int(event.get("haaEvent") or 0) == 1
    ]

    if len(haa_events) != STATE_HAA_EVENT_COUNT:
        raise ValueError(
            f"Expected {STATE_HAA_EVENT_COUNT} State HAA events, "
            f"found {len(haa_events)}"
        )

    targets = sum(int(event.get("targetQuantity") or 0) for event in haa_events)
    if targets != STATE_HAA_TARGETS:
        raise ValueError(
            f"Expected {STATE_HAA_TARGETS} State HAA targets, found {targets}"
        )

    event_types = {
        int(event.get("eventTypeId") or 0): int(event.get("targetQuantity") or 0)
        for event in haa_events
    }

    # SOS event types observed in the State report:
    # 1=Singles, 2=Doubles, 3=Handicap.
    expected = {1: 200, 2: 100, 3: 100}
    if event_types != expected:
        raise ValueError(
            f"Unexpected State HAA event composition: {event_types}"
        )


def _find_or_create_shooter(
    database,
    row: dict[str, Any],
) -> tuple[int | None, bool]:
    ata = _ata(row)
    name = _name(row)
    state = str(row.get("stateProvince") or "").strip().upper()

    if ata:
        rows = database.query(
            "SELECT id FROM shooters WHERE ata_number=?",
            (ata,),
        )
        if rows:
            return int(rows[0]["id"]), False

    if name:
        rows = database.query(
            """
            SELECT id FROM shooters
            WHERE lower(trim(display_name))=lower(trim(?))
            """,
            (name,),
        )
        if len(rows) == 1:
            return int(rows[0]["id"]), False

    if not name:
        return None, False

    shooter_id = database.upsert_shooter(
        ata,
        name,
        _category(row),
        state or "MN",
    )
    return int(shooter_id), True


def import_state_haa_report(
    database,
    report_path: Path,
    *,
    season: int = 2026,
    shoot_id: int = 4468,
    shoot_name: str = "2026 MN State Shoot",
    shoot_date: str = "2026-07-05",
) -> StateHAAImportResult:
    payload = _payload(report_path)
    validate_state_haa_report(payload)

    rows = payload.get("sortedReportData")
    if not isinstance(rows, list):
        raise ValueError("SOS State report has no sortedReportData list")

    mn_rows = 0
    completers = 0
    matched = 0
    created = 0
    written = 0

    for row in rows:
        if not isinstance(row, dict):
            continue

        if str(row.get("stateProvince") or "").strip().upper() != "MN":
            continue

        mn_rows += 1

        # This capture is the HAA view selected by the user. SOS reports exactly
        # three HAA events in eventsData, so eventsCompleted==3 means all three
        # State HAA components were completed. totalScore is NOT used to infer
        # discipline hits or season target totals.
        if int(row.get("eventsCompleted") or 0) != STATE_HAA_EVENT_COUNT:
            continue

        completers += 1

        shooter_id, was_created = _find_or_create_shooter(database, row)
        if shooter_id is None:
            continue

        matched += 1
        if was_created:
            created += 1

        save_record(
            database,
            HAARecord(
                season=season,
                shooter_id=shooter_id,
                route="STATE",
                shoot_name=shoot_name,
                shoot_date=shoot_date,
                shoot_zone="",
                resident_zone="",
                category=_category(row),
                singles_completed=True,
                handicap_completed=True,
                doubles_completed=True,
                source_url=f"SOS shoot {shoot_id}",
                source_label="SOS Clays State HAA report",
                source_coverage="COMPLETE",
                verified=True,
                notes=(
                    "SOS HAA report: eventsCompleted=3. eventsData confirms "
                    "the three HAA events are 200 Singles, 100 Doubles, "
                    "and 100 Handicap (400 targets shot at total)."
                ),
            ),
        )
        written += 1

    rebuild_season_haa_flags(database, season)

    return StateHAAImportResult(
        shoot_id=shoot_id,
        report_rows=len(rows),
        minnesota_rows=mn_rows,
        haa_completers=completers,
        shooter_matches=matched,
        shooter_creates=created,
        haa_records_written=written,
    )


def latest_state_report_capture() -> Path:
    roots = [
        DATA / "connector_downloads" / "sos",
    ]

    candidates = []
    for root in roots:
        if not root.exists():
            continue
        for folder in root.iterdir():
            if not folder.is_dir():
                continue
            for path in folder.glob("*shootHighGunReport.json"):
                candidates.append(path)

    if not candidates:
        raise FileNotFoundError("No captured SOS shootHighGunReport JSON found")

    return sorted(candidates, key=lambda path: path.stat().st_mtime)[-1]
