from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import re

from .connectors import SessionStore, _load_playwright


MYATA_URL = "https://shootata.com/Shooter-Information-Center"
DISCIPLINES = ("singles", "handicap", "doubles")


@dataclass
class MyATATotals:
    season: int
    ata_number: str
    display_name: str
    singles_targets: int = 0
    singles_hits: int = 0
    singles_average: float = 0.0
    handicap_targets: int = 0
    handicap_hits: int = 0
    handicap_average: float = 0.0
    doubles_targets: int = 0
    doubles_hits: int = 0
    doubles_average: float = 0.0
    source_url: str = MYATA_URL


@dataclass
class CaptureResult:
    directory: str
    page_url: str
    page_title: str
    tables: int
    json_responses: int
    totals_found: bool
    imported: bool
    warnings: list[str]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _clean(value).lower()).strip("_")


def _number(value: Any) -> float | None:
    text = _clean(value).replace(",", "").replace("%", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(round(number)) if number is not None else None


def _hits(targets: int, average_value: float) -> int:
    return int(round(targets * average_value / 100.0))


def normalize_table(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    header_index = 0
    best_score = -1
    for index, row in enumerate(rows[:8]):
        keys = [_key(cell) for cell in row]
        score = sum(
            any(word in key for word in ("target", "average", "singles", "handicap", "doubles", "year"))
            for key in keys
        )
        if score > best_score:
            best_score = score
            header_index = index

    headers = []
    used = {}
    for position, cell in enumerate(rows[header_index]):
        base = _key(cell) or f"column_{position + 1}"
        count = used.get(base, 0) + 1
        used[base] = count
        headers.append(base if count == 1 else f"{base}_{count}")

    output = []
    for row in rows[header_index + 1 :]:
        if not any(_clean(cell) for cell in row):
            continue
        padded = list(row) + [""] * max(0, len(headers) - len(row))
        output.append({headers[i]: _clean(padded[i]) for i in range(len(headers))})
    return output


def _find_value(row: dict[str, str], include: tuple[str, ...], exclude: tuple[str, ...] = ()) -> str:
    for key, value in row.items():
        if all(word in key for word in include) and not any(word in key for word in exclude):
            return value
    return ""


def _wide_totals(
    row: dict[str, str],
    season: int,
    ata_number: str,
    display_name: str,
) -> MyATATotals | None:
    year_value = (
        _find_value(row, ("target", "year"))
        or _find_value(row, ("year",))
        or _find_value(row, ("season",))
    )
    parsed_year = _integer(year_value)
    if parsed_year is not None and parsed_year != season:
        return None

    totals = MyATATotals(season=season, ata_number=ata_number, display_name=display_name)
    recognized = 0
    for discipline in DISCIPLINES:
        target_value = (
            _find_value(row, (discipline, "target"))
            or _find_value(row, (discipline, "registered"))
        )
        average_value = (
            _find_value(row, (discipline, "average"))
            or _find_value(row, (discipline, "avg"))
        )
        hit_value = _find_value(row, (discipline, "hit"))

        targets = _integer(target_value) or 0
        avg = _number(average_value) or 0.0
        hits = _integer(hit_value)
        if hits is None and targets and avg:
            hits = _hits(targets, avg)
        hits = hits or 0

        if targets or avg or hits:
            recognized += 1
        setattr(totals, f"{discipline}_targets", targets)
        setattr(totals, f"{discipline}_average", avg)
        setattr(totals, f"{discipline}_hits", hits)

    return totals if recognized >= 2 else None


def _discipline_totals(
    rows: list[dict[str, str]],
    season: int,
    ata_number: str,
    display_name: str,
) -> MyATATotals | None:
    totals = MyATATotals(season=season, ata_number=ata_number, display_name=display_name)
    recognized = set()

    for row in rows:
        joined = " ".join(row.values()).lower()
        discipline = next((name for name in DISCIPLINES if name in joined), None)
        if not discipline:
            continue

        year_value = _find_value(row, ("year",)) or _find_value(row, ("season",))
        parsed_year = _integer(year_value)
        if parsed_year is not None and parsed_year != season:
            continue

        targets = _integer(
            _find_value(row, ("target",), exclude=("year",))
            or _find_value(row, ("registered",), exclude=("year",))
        ) or 0
        avg = _number(
            _find_value(row, ("average",))
            or _find_value(row, ("avg",))
        ) or 0.0
        hits = _integer(_find_value(row, ("hit",)))
        if hits is None and targets and avg:
            hits = _hits(targets, avg)
        hits = hits or 0

        if targets or avg or hits:
            recognized.add(discipline)
            setattr(totals, f"{discipline}_targets", targets)
            setattr(totals, f"{discipline}_average", avg)
            setattr(totals, f"{discipline}_hits", hits)

    return totals if len(recognized) >= 2 else None


def parse_totals_from_tables(
    tables: list[list[list[str]]],
    season: int,
    ata_number: str,
    display_name: str = "",
) -> MyATATotals | None:
    normalized = [normalize_table(table) for table in tables]
    for rows in normalized:
        for row in rows:
            totals = _wide_totals(row, season, ata_number, display_name)
            if totals:
                return totals

    flattened = [row for rows in normalized for row in rows]
    return _discipline_totals(flattened, season, ata_number, display_name)


def upsert_official_totals(database, totals: MyATATotals) -> int:
    shooter_id = database.upsert_shooter(
        totals.ata_number,
        totals.display_name or f"ATA {totals.ata_number}",
        "MEN",
        "MN",
    )
    database.upsert_stats(
        shooter_id,
        totals.season,
        singles_targets=totals.singles_targets,
        singles_hits=totals.singles_hits,
        handicap_targets=totals.handicap_targets,
        handicap_hits=totals.handicap_hits,
        doubles_targets=totals.doubles_targets,
        doubles_hits=totals.doubles_hits,
        source="MyATA authenticated",
        official=1,
    )
    return shooter_id


def _extract_tables(page) -> list[list[list[str]]]:
    tables = []
    for table in page.locator("table").all():
        rows = []
        for row in table.locator("tr").all():
            cells = []
            for cell in row.locator("th, td").all():
                try:
                    cells.append(_clean(cell.inner_text(timeout=1500)))
                except Exception:
                    cells.append("")
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def _click_my_scores(page) -> None:
    selectors = (
        page.get_by_text("My Scores", exact=True),
        page.get_by_role("button", name=re.compile(r"my scores", re.I)),
        page.locator('input[value*="My Scores" i]'),
        page.locator('a:has-text("My Scores")'),
    )
    for locator in selectors:
        try:
            if locator.count():
                locator.first.click()
                page.wait_for_timeout(4000)
                return
        except Exception:
            continue
    raise RuntimeError("The authenticated My Scores control was not found")


def capture_myata(
    data_dir: Path,
    *,
    season: int,
    ata_number: str,
    database=None,
    headed: bool = False,
) -> CaptureResult:
    ata = "".join(ch for ch in str(ata_number or "") if ch.isdigit())
    if not ata:
        raise ValueError("Set user_ata_number in Settings before importing MyATA")

    store = SessionStore(data_dir)
    profile = store.profile_dir("shootata")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(data_dir) / "connector_downloads" / "myata" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    json_payloads = []
    warnings = []
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=not headed,
            viewport={"width": 1450, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()

        def on_response(response):
            try:
                content_type = (response.headers.get("content-type") or "").lower()
                if "json" not in content_type:
                    return
                url = response.url
                if "shootata" not in url.lower():
                    return
                body = response.json()
                json_payloads.append({"url": url, "body": body})
            except Exception:
                return

        page.on("response", on_response)
        page.goto(MYATA_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        _click_my_scores(page)
        page.wait_for_timeout(3000)

        tables = _extract_tables(page)
        title = page.title()
        url = page.url
        body_text = ""
        try:
            body_text = page.locator("body").inner_text(timeout=10000)
        except Exception:
            warnings.append("Could not capture page body text")

        (output_dir / "page_text.txt").write_text(body_text, encoding="utf-8")
        (output_dir / "tables.json").write_text(
            json.dumps(tables, indent=2),
            encoding="utf-8",
        )
        (output_dir / "network_json.json").write_text(
            json.dumps(json_payloads, indent=2, default=str),
            encoding="utf-8",
        )
        (output_dir / "page_meta.json").write_text(
            json.dumps(
                {"url": url, "title": title, "season": season, "ata_number": ata},
                indent=2,
            ),
            encoding="utf-8",
        )
        context.close()

    totals = parse_totals_from_tables(tables, season, ata)
    imported = False
    if totals and database is not None:
        upsert_official_totals(database, totals)
        imported = True
        (output_dir / "official_totals.json").write_text(
            json.dumps(asdict(totals), indent=2),
            encoding="utf-8",
        )
    elif not totals:
        warnings.append(
            "Official totals were not recognized automatically. "
            "The sanitized table and network captures were saved for parser refinement."
        )

    return CaptureResult(
        directory=str(output_dir),
        page_url=url,
        page_title=title,
        tables=len(tables),
        json_responses=len(json_payloads),
        totals_found=totals is not None,
        imported=imported,
        warnings=warnings,
    )
