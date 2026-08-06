from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urljoin, urlparse
import csv
import json
import re

from bs4 import BeautifulSoup

from .shootscoreboard_web import (
    BASE_URL,
    fetch_text,
    import_public_shoot,
    load_public_shoot,
)


TARGET_YEAR = 2026
TARGET_YEAR_START = date(2025, 9, 1)
TARGET_YEAR_END = date(2026, 8, 31)


@dataclass
class ShootCandidate:
    shoot_id: int
    name: str
    club: str
    state: str
    start_date: str
    end_date: str
    source_url: str
    in_target_year: bool
    selected: bool = True


@dataclass
class ShootSyncResult:
    shoot_id: int
    name: str
    status: str
    events_found: int = 0
    rows_found: int = 0
    rows_imported: int = 0
    shooters_created: int = 0
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class RaceSyncSummary:
    target_year: int
    started_at: str
    finished_at: str
    candidates: int
    attempted: int
    imported_shoots: int
    duplicate_shoots: int
    failed_shoots: int
    score_rows_imported: int
    shooters_created: int
    results: list[ShootSyncResult]


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date: {value!r}")


def in_target_year(start_date: str, end_date: str) -> bool:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    return start >= TARGET_YEAR_START and end <= TARGET_YEAR_END


def _shoot_id_from_href(href: str) -> int | None:
    parsed = urlparse(urljoin(BASE_URL, href))
    query = parse_qs(parsed.query)
    values = query.get("shootid")
    if not values or not values[0].isdigit():
        return None
    return int(values[0])


def discover_minnesota_shoots_from_html(html: str) -> list[ShootCandidate]:
    """Parse Minnesota shoot rows from ShootScoreBoard's public listing."""
    soup = BeautifulSoup(html, "html.parser")
    candidates: dict[int, ShootCandidate] = {}

    for anchor in soup.find_all("a", href=True):
        shoot_id = _shoot_id_from_href(anchor["href"])
        if shoot_id is None:
            continue

        row = anchor.find_parent("tr")
        container = row if row is not None else anchor.parent
        text = " ".join(container.get_text(" ", strip=True).split())
        upper = text.upper()

        if not re.search(r"(?:,\s*|\b)MN(?:\b|$)", upper):
            continue

        dates = re.findall(r"\d{2}/\d{2}/\d{4}", text)
        if not dates:
            continue
        start_raw = dates[0]
        end_raw = dates[1] if len(dates) > 1 else dates[0]

        name = " ".join(anchor.get_text(" ", strip=True).split())
        if not name or name.upper() in {"SCORES", "MENU", "RESULTS"}:
            cells = row.find_all(["td", "th"]) if row else []
            name = " ".join(cells[0].get_text(" ", strip=True).split()) if cells else text

        club = ""
        cells = row.find_all(["td", "th"]) if row else []
        for cell in cells:
            cell_text = " ".join(cell.get_text(" ", strip=True).split())
            if re.search(r",\s*MN\b", cell_text.upper()):
                club = re.sub(r",\s*MN\b.*$", "", cell_text, flags=re.I).strip()
                break

        start_iso = _parse_date(start_raw).isoformat()
        end_iso = _parse_date(end_raw).isoformat()
        target_year = in_target_year(start_iso, end_iso)
        candidates[shoot_id] = ShootCandidate(
            shoot_id=shoot_id,
            name=name,
            club=club,
            state="MN",
            start_date=start_iso,
            end_date=end_iso,
            source_url=urljoin(BASE_URL, anchor["href"]),
            in_target_year=target_year,
            selected=target_year,
        )

    return sorted(candidates.values(), key=lambda item: (item.start_date, item.shoot_id))


def discover_current_minnesota_shoots(
    fetcher: Callable[[str], str] = fetch_text,
) -> list[ShootCandidate]:
    html = fetcher(BASE_URL)
    return [
        candidate
        for candidate in discover_minnesota_shoots_from_html(html)
        if candidate.in_target_year
    ]


def validate_loaded_shoot(shoot: Any, allow_out_of_season: bool = False) -> None:
    if allow_out_of_season:
        return
    if not in_target_year(shoot.start_date, shoot.end_date):
        raise ValueError(
            f"{shoot.name} ({shoot.start_date} through {shoot.end_date}) is outside "
            f"the active 2026 target year ({TARGET_YEAR_START} through {TARGET_YEAR_END})."
        )


def write_candidate_csv(candidates: list[ShootCandidate], path: Path) -> Path:
    fields = [
        "selected",
        "shoot_id",
        "name",
        "club",
        "state",
        "start_date",
        "end_date",
        "source_url",
        "in_target_year",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for candidate in candidates:
            row = asdict(candidate)
            row["selected"] = "yes" if candidate.selected else "no"
            row["in_target_year"] = "yes" if candidate.in_target_year else "no"
            writer.writerow(row)
    return path


def read_candidate_csv(path: Path) -> list[ShootCandidate]:
    candidates = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            selected = str(row.get("selected", "yes")).strip().lower() in {
                "1", "yes", "true", "y"
            }
            candidate = ShootCandidate(
                shoot_id=int(row["shoot_id"]),
                name=row.get("name", ""),
                club=row.get("club", ""),
                state=row.get("state", "MN"),
                start_date=row["start_date"],
                end_date=row["end_date"],
                source_url=row.get("source_url", ""),
                in_target_year=in_target_year(row["start_date"], row["end_date"]),
                selected=selected,
            )
            candidates.append(candidate)
    return candidates


def sync_current_race(
    database,
    candidates: list[ShootCandidate],
    matcher_threshold: int = 88,
    allow_out_of_season: bool = False,
    loader=load_public_shoot,
) -> RaceSyncSummary:
    started = datetime.now().isoformat(timespec="seconds")
    results: list[ShootSyncResult] = []

    for candidate in candidates:
        if not candidate.selected:
            continue

        result = ShootSyncResult(
            shoot_id=candidate.shoot_id,
            name=candidate.name,
            status="pending",
        )
        try:
            if not allow_out_of_season and not candidate.in_target_year:
                raise ValueError("Shoot is outside the active 2026 target year")

            shoot = loader(candidate.shoot_id)
            validate_loaded_shoot(shoot, allow_out_of_season=allow_out_of_season)
            imported = import_public_shoot(
                database,
                shoot,
                TARGET_YEAR,
                mn_only=True,
                club=candidate.club or shoot.name,
                matcher_threshold=matcher_threshold,
            )
            result.events_found = imported.events_found
            result.rows_found = imported.score_rows_found
            result.rows_imported = imported.score_rows_imported
            result.shooters_created = imported.shooters_created
            result.warnings = list(imported.warnings)
            result.status = (
                "duplicate"
                if imported.score_rows_imported == 0
                and any("already imported" in warning.lower() for warning in imported.warnings)
                else "imported"
            )
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
        results.append(result)

    finished = datetime.now().isoformat(timespec="seconds")
    return RaceSyncSummary(
        target_year=TARGET_YEAR,
        started_at=started,
        finished_at=finished,
        candidates=len(candidates),
        attempted=len(results),
        imported_shoots=sum(item.status == "imported" for item in results),
        duplicate_shoots=sum(item.status == "duplicate" for item in results),
        failed_shoots=sum(item.status == "failed" for item in results),
        score_rows_imported=sum(item.rows_imported for item in results),
        shooters_created=sum(item.shooters_created for item in results),
        results=results,
    )


def write_sync_report(summary: RaceSyncSummary, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    return path
