from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from .normalization import (
    inferred_state,
    normalize_event_date,
    normalize_shoot_name,
)
from .source_adapters import observe_myata_details


@dataclass
class MyATACaptureImportResult:
    capture_directory: str
    ata_number: str
    member_name: str
    detail_rows_found: int
    observations_imported: int
    shooter_id: int
    warnings: list[str]


def _responses(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("network_json.json must contain a list")
    return data


def extract_myata_payloads(
    network_path: Path,
    season: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    member: dict[str, Any] = {}
    details: list[dict[str, Any]] = []
    warnings: list[str] = []

    for response in _responses(network_path):
        url = str(response.get("url") or "")
        body = response.get("body")

        if "GetMemberInfo" in url and isinstance(body, dict):
            member = body

        if "GetMemberStatsDetails" in url and isinstance(body, dict):
            if f"year={season}" not in url:
                continue
            rows = body.get("MemberPerformanceInfos")
            if isinstance(rows, list):
                details.extend(row for row in rows if isinstance(row, dict))

    if not member:
        warnings.append("GetMemberInfo was not found in the capture")
    if not details:
        warnings.append(
            f"GetMemberStatsDetails for target year {season} was not found"
        )
    return member, details, warnings


def normalize_myata_detail_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = dict(row)
        raw_date = str(item.get("Date") or "")
        raw_name = str(item.get("Name") or "")

        # Administrative records have no registered target scores.
        target_fields = (
            "SinglesShot",
            "SinglesLeagueShot",
            "HandicapShot",
            "DoublesShot",
            "DoublesLeagueShot",
        )
        if not any(int(item.get(field) or 0) for field in target_fields):
            continue

        item["Date"] = normalize_event_date(raw_date)
        item["Name"] = normalize_shoot_name(raw_name)
        item["State"] = inferred_state(raw_name)
        normalized.append(item)
    return normalized


def import_myata_capture(
    database,
    capture_directory: Path,
    season: int,
    expected_ata_number: str = "",
) -> MyATACaptureImportResult:
    capture_directory = Path(capture_directory)
    network_path = capture_directory / "network_json.json"
    if not network_path.exists():
        raise FileNotFoundError(network_path)

    member, details, warnings = extract_myata_payloads(network_path, season)
    ata_number = "".join(
        character
        for character in str(member.get("AtaNumber") or expected_ata_number)
        if character.isdigit()
    )
    member_name = " ".join(str(member.get("MemberName") or "").split())

    if not ata_number:
        raise ValueError("No ATA number was found in the MyATA capture")
    expected = "".join(character for character in expected_ata_number if character.isdigit())
    if expected and ata_number != expected:
        raise ValueError(
            f"Capture ATA number {ata_number} does not match expected ATA number {expected}"
        )

    shooter_id = database.upsert_shooter(
        ata_number,
        member_name or f"ATA {ata_number}",
        "MEN",
        "MN",
    )

    normalized = normalize_myata_detail_rows(details)
    imported = observe_myata_details(
        database,
        shooter_id,
        season,
        normalized,
    )

    return MyATACaptureImportResult(
        capture_directory=str(capture_directory),
        ata_number=ata_number,
        member_name=member_name,
        detail_rows_found=len(normalized),
        observations_imported=imported,
        shooter_id=shooter_id,
        warnings=warnings,
    )


def latest_capture(root: Path) -> Path:
    root = Path(root)
    candidates = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir() and (path / "network_json.json").exists()
        ),
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No MyATA captures found under {root}")
    return candidates[0]
