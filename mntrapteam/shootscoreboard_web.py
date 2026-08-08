from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
import hashlib
import re

from bs4 import BeautifulSoup

from .matcher import ShooterMatcher


BASE_URL = "https://shootscoreboard.com/"
USER_AGENT = "MNTrapTeam/2.4 (+public-score-import)"
DISCIPLINE_WORDS = {
    "SINGLES": "singles",
    "16 YARD": "singles",
    "16-YARD": "singles",
    "16YARD": "singles",
    "HANDICAP": "handicap",
    "DOUBLES": "doubles",
}


@dataclass
class WebEvent:
    event_id: int
    name: str
    discipline: str
    entries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WebShoot:
    shoot_id: int
    name: str
    start_date: str
    end_date: str
    source_url: str
    events: list[WebEvent] = field(default_factory=list)


@dataclass
class WebImportResult:
    shoot_id: int
    shoot_name: str
    events_found: int
    score_rows_found: int
    score_rows_imported: int
    shooters_created: int
    warnings: list[str] = field(default_factory=list)


def fetch_text(url: str, timeout: int = 30) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def extract_shoot_id(value: str | int) -> int:
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("shoot_id must be positive")
        return value
    text = str(value).strip()
    if text.isdigit():
        value_int = int(text)
        if value_int <= 0:
            raise ValueError("shoot_id must be positive")
        return value_int
    parsed = urlparse(text)
    values = parse_qs(parsed.query).get("shootid")
    if not values or not values[0].isdigit():
        raise ValueError("Enter a ShootScoreBoard shoot ID or URL containing shootid=")
    return int(values[0])


def parse_shoot_header(html: str, shoot_id: int) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    date_match = re.search(
        r"\((\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})\)",
        text,
    )
    if date_match:
        raw_start, raw_end = date_match.groups()
    else:
        single = re.search(r"\((\d{2}/\d{2}/\d{4})\)", text)
        if not single:
            raise ValueError("Could not identify shoot dates")
        raw_start = raw_end = single.group(1)

    def iso(raw: str) -> str:
        month, day, year = raw.split("/")
        return f"{year}-{month}-{day}"

    title = ""
    for candidate in soup.stripped_strings:
        cleaned = " ".join(candidate.split())
        if (
            "SHOOT" in cleaned.upper()
            and "SHOOTSCOREBOARD" not in cleaned.upper()
            and not cleaned.startswith("(")
        ):
            title = cleaned
            break
    if not title:
        title = f"ShootScoreBoard Shoot {shoot_id}"
    return title, iso(raw_start), iso(raw_end)


def discover_event_ids(entries_html: str, shoot_id: int) -> list[int]:
    soup = BeautifulSoup(entries_html, "html.parser")
    ids: set[int] = set()
    for anchor in soup.find_all("a", href=True):
        parsed = urlparse(anchor["href"])
        query = parse_qs(parsed.query)
        if query.get("shootid", [""])[0] != str(shoot_id):
            continue
        event = query.get("sorteventid", [""])[0]
        if event.isdigit():
            ids.add(int(event))
    if not ids:
        visible = soup.get_text(" ", strip=True)
        ids.update(int(value) for value in re.findall(r"\bE(\d+)\b", visible))
    return sorted(ids)


def discipline_from_title(title: str) -> str:
    upper = title.upper()
    for word, discipline in DISCIPLINE_WORDS.items():
        if word in upper:
            return discipline
    raise ValueError(f"Unrecognized event discipline: {title}")


def parse_event_report(html: str, event_id: int) -> WebEvent:
    soup = BeautifulSoup(html, "html.parser")
    visible = soup.get_text("\n", strip=True)
    match = re.search(
        rf"EVENT\s+{event_id}\s*-\s*(.+?)(?:\n|\r|$)",
        visible,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"Could not identify Event {event_id} title")
    title = " ".join(match.group(1).split())
    discipline = discipline_from_title(title)

    table = None
    header_cells = []
    for candidate in soup.find_all("table"):
        first = candidate.find("tr")
        if not first:
            continue
        headers = [
            " ".join(cell.get_text(" ", strip=True).split()).upper()
            for cell in first.find_all(["td", "th"])
        ]
        if {"NAME", "STATE", "TOTAL"}.issubset(set(headers)):
            table = candidate
            header_cells = headers
            break
    if table is None:
        raise ValueError(f"No shooter table found for Event {event_id}")

    index = {name: position for position, name in enumerate(header_cells)}
    entries = []
    rows = table.find_all("tr")
    for row in rows[1:]:
        cells = [
            " ".join(cell.get_text(" ", strip=True).split())
            for cell in row.find_all(["td", "th"])
        ]
        if len(cells) < len(header_cells):
            continue
        name = cells[index["NAME"]].strip()
        state = cells[index["STATE"]].strip().upper()
        total_text = cells[index["TOTAL"]].replace(",", "").strip()
        if not name or not total_text.isdigit():
            continue
        scores_text = cells[index["SCORES"]] if "SCORES" in index else ""
        sub_scores = [int(value) for value in re.findall(r"\d+", scores_text)]
        total = int(total_text)
        if sub_scores and sum(sub_scores) != total:
            sub_scores = []

        if discipline == "singles":
            targets = max(100, len(sub_scores) * 25) if sub_scores else (200 if total > 100 else 100)
        elif discipline == "doubles":
            targets = max(100, len(sub_scores) * 50) if sub_scores else 100
        else:
            targets = 100

        class_or_yardage = cells[index["CLASS/YDG"]] if "CLASS/YDG" in index else ""
        category = cells[index["CATEGORY"]] if "CATEGORY" in index else ""
        squad_post = cells[index["SQUAD/POST"]] if "SQUAD/POST" in index else ""

        entries.append(
            {
                "name": name,
                "state": state,
                "category": category.strip().upper(),
                "class_or_yardage": class_or_yardage.strip(),
                "squad_post": squad_post.strip(),
                "sub_scores": sub_scores,
                "targets": targets,
                "hits": total,
            }
        )
    return WebEvent(event_id, title, discipline, entries)


def load_public_shoot(shoot: str | int, fetcher=fetch_text) -> WebShoot:
    shoot_id = extract_shoot_id(shoot)
    menu_url = f"{BASE_URL}menu.cfm?shootid={shoot_id}"
    entries_url = f"{BASE_URL}entrys.cfm?shootid={shoot_id}"
    name, start_date, end_date = parse_shoot_header(fetcher(menu_url), shoot_id)
    event_ids = discover_event_ids(fetcher(entries_url), shoot_id)
    if not event_ids:
        raise ValueError("No event reports were found for this shoot")
    events = []
    for event_id in event_ids:
        url = f"{BASE_URL}reports.cfm?shootid={shoot_id}&sorteventid={event_id}"
        try:
            event = parse_event_report(fetcher(url), event_id)
        except ValueError:
            # Public ShootScoreBoard pages sometimes include AIM/youth,
            # preliminary, or malformed event pages.  Those should not cause
            # the entire shoot to be discarded when other ATA events are valid.
            continue
        events.append(event)
    if not events:
        raise ValueError("No supported ATA event reports were found for this shoot")
    return WebShoot(shoot_id, name, start_date, end_date, menu_url, events)


def import_public_shoot(
    database,
    shoot: WebShoot,
    season: int,
    mn_only: bool = True,
    club: str = "",
    matcher_threshold: int = 88,
    in_state: bool = True,
) -> WebImportResult:
    signature = "|".join(
        f"{event.event_id}:{len(event.entries)}:"
        + ",".join(f"{row['name']}:{row['hits']}:{row['targets']}" for row in event.entries)
        for event in shoot.events
    )
    digest = hashlib.sha256(
        f"shootscoreboard-web:{shoot.shoot_id}|{signature}".encode("utf-8")
    ).hexdigest()
    if database.query("SELECT id FROM imports WHERE sha256=?", (digest,)):
        return WebImportResult(
            shoot.shoot_id,
            shoot.name,
            len(shoot.events),
            sum(len(event.entries) for event in shoot.events),
            0,
            0,
            ["This exact public shoot version was already imported"],
        )

    shoot_row_id = database.execute(
        """
        INSERT OR IGNORE INTO shoots(
            name, club, city, state, start_date, end_date, source_type, source_url
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            shoot.name,
            club,
            "",
            "MN" if in_state else "",
            shoot.start_date,
            shoot.end_date,
            "ShootScoreBoard web",
            shoot.source_url,
        ),
    )
    if not shoot_row_id:
        rows = database.query(
            "SELECT id FROM shoots WHERE name=? AND start_date=? AND source_url=?",
            (shoot.name, shoot.start_date, shoot.source_url),
        )
        shoot_row_id = rows[0]["id"]

    matcher = ShooterMatcher(database, matcher_threshold)
    imported = 0
    created = 0
    warnings = []

    for event in shoot.events:
        for row in event.entries:
            if mn_only and row["state"] != "MN":
                continue
            shooter_id, _confidence = matcher.match(row["name"], "")
            if shooter_id is None:
                shooter_id = database.upsert_shooter(
                    "",
                    row["name"],
                    row["category"] or "MEN",
                    row["state"] or "MN",
                )
                created += 1
                warnings.append(f"Created shooter without ATA number: {row['name']}")

            database.execute(
                """
                INSERT OR REPLACE INTO scores(
                    shooter_id, shoot_id, event_date, event_name,
                    discipline, targets, hits, in_state, club_key,
                    source, official, raw_name
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    shooter_id,
                    shoot_row_id,
                    shoot.start_date,
                    event.name,
                    event.discipline,
                    row["targets"],
                    row["hits"],
                    int(in_state),
                    club or shoot.name,
                    "ShootScoreBoard web",
                    0,
                    row["name"],
                ),
            )
            imported += 1

    database.execute(
        """
        INSERT INTO imports(
            filename, kind, sha256, rows_read, rows_imported, warnings
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            shoot.source_url,
            "scoreboard-web",
            digest,
            sum(len(event.entries) for event in shoot.events),
            imported,
            "\n".join(warnings),
        ),
    )
    from .importers import ScoreboardImporter
    ScoreboardImporter(database, matcher_threshold).rebuild_stats(season)
    return WebImportResult(
        shoot.shoot_id,
        shoot.name,
        len(shoot.events),
        sum(len(event.entries) for event in shoot.events),
        imported,
        created,
        warnings,
    )
