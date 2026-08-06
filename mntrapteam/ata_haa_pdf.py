from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.request import Request, urlopen
import re

import pdfplumber

from .haa_gate import HAARecord, normalize_route, normalize_zone, save_record


USER_AGENT = "MNTrapTeam/2.7 ATA-HAA-Importer"
ATA_HEADERS = {"ATA NO.", "ATA NO", "ATA #", "ATA NUMBER"}
NAME_HEADERS = {"NAME", "SHOOTER", "SHOOTER NAME"}
STATE_HEADERS = {"STATE", "ST"}
SCORE_HEADERS = {"SCORE", "TOTAL", "HAA SCORE"}
CATEGORY_HEADERS = {
    "CLASS/CATEGORY/PLACE",
    "CLASS / CATEGORY / PLACE",
    "CATEGORY",
    "CLASS/CATEGORY",
}


@dataclass
class ATAHAAEntry:
    ata_number: str
    name: str
    city: str
    state: str
    score: int | None
    category_text: str
    category: str


@dataclass
class ATAHAAImportResult:
    source: str
    rows_found: int
    minnesota_rows: int
    rows_imported: int
    shooters_created: int
    shooters_updated: int
    warnings: list[str]


def download_pdf(url: str, destination: Path | None = None) -> Path:
    if destination is None:
        handle = NamedTemporaryFile(delete=False, suffix=".pdf")
        destination = Path(handle.name)
        handle.close()

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,*/*",
        },
    )
    with urlopen(request, timeout=45) as response:
        data = response.read()

    if not data.startswith(b"%PDF"):
        raise ValueError("The downloaded source is not a PDF")
    destination.write_bytes(data)
    return destination


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _header_key(value: Any) -> str:
    return _clean(value).upper()


def _find_header(headers: list[str], accepted: set[str]) -> int | None:
    for index, header in enumerate(headers):
        if header in accepted:
            return index
    return None


def category_from_text(value: str) -> str:
    upper = _clean(value).upper().replace("-", " ")
    mappings = (
        (("SUB JUNIOR", "SUB JR"), "SUB_JR"),
        (("JUNIOR GOLD",), "JUNIOR_GOLD"),
        (("LADY II", "LADY 2"), "LADY_II"),
        (("LADY I", "LADY 1"), "LADY_I"),
        (("SENIOR VETERAN", "SR VET"), "SENIOR_VETERAN"),
        (("SUB VETERAN", "SUB VET"), "SUB_VETERAN"),
        (("VETERAN",), "VETERAN"),
        (("JUNIOR",), "JUNIOR"),
        (("CHAIR",), "CHAIR"),
    )
    for needles, category in mappings:
        if any(needle in upper for needle in needles):
            return category
    return "MEN"


def _int_or_none(value: Any) -> int | None:
    text = re.sub(r"[^\d]", "", _clean(value))
    return int(text) if text else None


def _valid_ata(value: Any) -> str:
    ata = re.sub(r"[^\d]", "", _clean(value))
    if not ata:
        return ""
    if len(ata) < 5 or len(ata) > 10:
        return ""
    return ata


def _candidate_tables(pdf_path: Path):
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables() or []:
                if table:
                    yield page_number, table


def parse_ata_haa_pdf(pdf_path: Path) -> tuple[list[ATAHAAEntry], list[str]]:
    entries: list[ATAHAAEntry] = []
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()

    for page_number, table in _candidate_tables(pdf_path):
        header_row_index = None
        headers: list[str] = []
        for index, row in enumerate(table[:5]):
            candidate = [_header_key(cell) for cell in row]
            if (
                _find_header(candidate, ATA_HEADERS) is not None
                and _find_header(candidate, NAME_HEADERS) is not None
            ):
                header_row_index = index
                headers = candidate
                break

        if header_row_index is None:
            continue

        ata_index = _find_header(headers, ATA_HEADERS)
        name_index = _find_header(headers, NAME_HEADERS)
        state_index = _find_header(headers, STATE_HEADERS)
        score_index = _find_header(headers, SCORE_HEADERS)
        category_index = _find_header(headers, CATEGORY_HEADERS)

        city_index = None
        for index, header in enumerate(headers):
            if header == "CITY":
                city_index = index
                break

        for row in table[header_row_index + 1 :]:
            cells = [_clean(cell) for cell in row]
            if ata_index is None or name_index is None:
                continue
            if max(ata_index, name_index) >= len(cells):
                continue

            ata = _valid_ata(cells[ata_index])
            name = cells[name_index]
            if not ata or not name:
                continue

            state = (
                cells[state_index].upper()
                if state_index is not None and state_index < len(cells)
                else ""
            )
            city = (
                cells[city_index]
                if city_index is not None and city_index < len(cells)
                else ""
            )
            score = (
                _int_or_none(cells[score_index])
                if score_index is not None and score_index < len(cells)
                else None
            )
            category_text = (
                cells[category_index]
                if category_index is not None and category_index < len(cells)
                else ""
            )

            key = (ata, name.upper())
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                ATAHAAEntry(
                    ata_number=ata,
                    name=name,
                    city=city,
                    state=state,
                    score=score,
                    category_text=category_text,
                    category=category_from_text(category_text),
                )
            )

    if not entries:
        warnings.append(
            "No table containing both a shooter name and ATA number was found."
        )
    return entries, warnings


def _existing_shooter(database, ata_number: str) -> dict[str, Any] | None:
    rows = database.query(
        "SELECT * FROM shooters WHERE ata_number=?",
        (ata_number,),
    )
    return rows[0] if rows else None


def import_ata_haa_pdf(
    database,
    pdf_path: Path,
    *,
    season: int,
    route: str,
    shoot_name: str,
    shoot_date: str,
    shoot_zone: str = "",
    source_url: str = "",
    source_label: str = "",
    source_coverage: str = "PARTIAL",
    minnesota_only: bool = True,
) -> ATAHAAImportResult:
    route = normalize_route(route)
    shoot_zone = normalize_zone(shoot_zone)
    coverage = source_coverage.strip().upper()

    if route not in {"STATE", "ZONE"}:
        raise ValueError("route must be STATE or ZONE")
    if route == "ZONE" and shoot_zone not in {"CENTRAL", "NORTHERN", "SOUTHERN"}:
        raise ValueError("A valid shoot_zone is required for a Zone HAA")
    if coverage not in {"PARTIAL", "COMPLETE"}:
        raise ValueError("source_coverage must be PARTIAL or COMPLETE")

    entries, warnings = parse_ata_haa_pdf(pdf_path)
    imported = 0
    created = 0
    updated = 0
    mn_rows = 0

    for entry in entries:
        if minnesota_only and entry.state and entry.state != "MN":
            continue
        mn_rows += 1

        existing = _existing_shooter(database, entry.ata_number)
        if existing:
            shooter_id = existing["id"]
            updated += 1
            database.execute(
                """
                UPDATE shooters
                SET display_name=?, state=?, category=?, active=1
                WHERE id=?
                """,
                (
                    entry.name,
                    entry.state or "MN",
                    entry.category,
                    shooter_id,
                ),
            )
        else:
            shooter_id = database.upsert_shooter(
                entry.ata_number,
                entry.name,
                entry.category,
                entry.state or "MN",
            )
            created += 1

        record = HAARecord(
            season=season,
            shooter_id=shooter_id,
            route=route,
            shoot_name=shoot_name,
            shoot_date=shoot_date,
            shoot_zone=shoot_zone,
            resident_zone=shoot_zone if route == "ZONE" else "",
            category=entry.category,
            singles_completed=True,
            handicap_completed=True,
            doubles_completed=entry.category != "SUB_JR",
            source_url=source_url,
            source_label=source_label or pdf_path.name,
            source_coverage=coverage,
            verified=True,
            notes=(
                f"ATA-bearing HAA result; score={entry.score}; "
                f"source category={entry.category_text}"
            ),
        )
        save_record(database, record)
        imported += 1

    from .haa_gate import rebuild_season_haa_flags
    rebuild_season_haa_flags(database, season)

    if coverage == "PARTIAL":
        warnings.append(
            "This source is marked PARTIAL. Imported shooters are confirmed "
            "HAA completers, but absent shooters must not be treated as non-completers."
        )

    return ATAHAAImportResult(
        source=str(pdf_path),
        rows_found=len(entries),
        minnesota_rows=mn_rows,
        rows_imported=imported,
        shooters_created=created,
        shooters_updated=updated,
        warnings=warnings,
    )


def import_ata_haa_url(database, url: str, **kwargs) -> ATAHAAImportResult:
    temp_path = download_pdf(url)
    try:
        return import_ata_haa_pdf(
            database,
            temp_path,
            source_url=url,
            **kwargs,
        )
    finally:
        temp_path.unlink(missing_ok=True)
