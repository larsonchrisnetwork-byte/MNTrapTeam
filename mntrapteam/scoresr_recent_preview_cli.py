from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .database import Database
from .paths import DATA
from .state_team_lock import ensure_schema as ensure_lock_schema


UA = "Mozilla/5.0 MNTrapTeam/5.0.1"
HOME = "https://www.scoresr.com/"
LIST_URL = "https://www.scoresr.com/regv2/PublicIfShowClubShoots.php"
DATA_URL = "https://www.scoresr.com/regv2/PublicIfShowData.php"


@dataclass(frozen=True)
class Candidate:
    ata_number: str
    display_name: str
    first_name: str
    last_name: str


@dataclass(frozen=True)
class Club:
    club_id: int
    club_name: str


@dataclass(frozen=True)
class Program:
    club_id: int
    club_name: str
    program_id: int
    label: str
    start_date: date | None
    end_date: date | None


def fetch_get(url: str, timeout: int = 15) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_post(url: str, fields: dict, timeout: int = 15) -> str:
    body = urlencode(fields).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def pool(db: Database, season: int) -> list[Candidate]:
    ensure_lock_schema(db)
    rows = db.query(
        """
        SELECT s.ata_number, s.display_name,
               COALESCE(s.first_name,'') AS first_name,
               COALESCE(s.last_name,'') AS last_name
        FROM state_team_qualification_lock l
        JOIN shooters s ON s.id=l.shooter_id
        WHERE l.season=? AND l.verified=1 AND l.state_team='MEN'
        ORDER BY s.display_name
        """,
        (season,),
    )
    return [
        Candidate(
            str(r["ata_number"] or "").strip(),
            str(r["display_name"] or "").strip(),
            str(r["first_name"] or "").strip(),
            str(r["last_name"] or "").strip(),
        )
        for r in rows if str(r["ata_number"] or "").strip()
    ]


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.upper().replace(",", " ").replace(".", " ")
    value = re.sub(r"[^A-Z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def match_row(row: list[str], candidates: list[Candidate]):
    joined = " | ".join(row)
    tokens = set(norm(joined).split())

    exact = []
    named = []

    for c in candidates:
        if c.ata_number and c.ata_number in joined:
            exact.append((c, "ATA"))
            continue

        first = norm(c.first_name)
        last = norm(c.last_name)
        if not first or not last:
            parts = norm(c.display_name).split()
            if len(parts) >= 2:
                first, last = parts[0], parts[-1]

        if first and last and first in tokens and last in tokens:
            named.append((c, "NAME"))

    if len(exact) == 1:
        return exact

    unique = {}
    for c, method in named:
        unique[c.ata_number] = (c, method)
    if len(unique) == 1:
        return list(unique.values())

    return []


def parse_dates(label: str):
    m = re.match(
        r"\s*(\d{2})-(\d{2})-(\d{4})\s*-\s*(\d{2})-(\d{2})-(\d{4})",
        label,
    )
    if not m:
        return None, None
    m1, d1, y1, m2, d2, y2 = map(int, m.groups())
    return date(y1, m1, d1), date(y2, m2, d2)


def clubs_from_home() -> list[Club]:
    html = fetch_get(HOME)
    soup = BeautifulSoup(html, "html.parser")
    found = {}

    for a in soup.find_all("a", href=True):
        href = urljoin(HOME, a["href"])
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)

        club_id = None
        club_name = ""

        if "PublicIfShowShootProgram.php" in parsed.path:
            vals = qs.get("clubId", [])
            names = qs.get("clubName", [])
            if vals:
                club_id = vals[0]
                club_name = names[0] if names else ""
        elif "ShootICMain.php" in parsed.path:
            vals = qs.get("forwardClubId", [])
            names = qs.get("forwardClubName", [])
            if vals:
                club_id = vals[0]
                club_name = names[0] if names else ""

        if not club_id or not str(club_id).isdigit():
            continue

        name = club_name.replace("+", " ").strip() or f"Club {club_id}"
        found[int(club_id)] = Club(int(club_id), name)

    return sorted(found.values(), key=lambda c: c.club_name)


def programs_for_club(club: Club) -> list[Program]:
    html = fetch_get(f"{LIST_URL}?clubId={club.club_id}&programId=0")
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", attrs={"name": "programId"})
    result = []

    if not select:
        return result

    for opt in select.find_all("option"):
        value = (opt.get("value") or "").strip()
        label = " ".join(opt.stripped_strings).strip()
        if not value.isdigit() or not label:
            continue
        start, end = parse_dates(label)
        result.append(
            Program(
                club.club_id,
                club.club_name,
                int(value),
                label,
                start,
                end,
            )
        )
    return result


def event_codes(program: Program):
    html = fetch_get(
        f"{LIST_URL}?clubId={program.club_id}&programId={program.program_id}"
    )
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", attrs={"name": "viewWhatSelect"})
    out = []
    if not select:
        return out
    for opt in select.find_all("option"):
        value = (opt.get("value") or "").strip()
        label = " ".join(opt.stripped_strings).strip()
        if re.fullmatch(r"s\d+", value):
            out.append((value, label))
    return out


def rows(html: str):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tr in soup.find_all("tr"):
        cells = [
            " ".join(c.stripped_strings).strip()
            for c in tr.find_all(["th", "td"])
        ]
        if cells:
            out.append(cells)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan recent ScoresR programs at exposed clubs for frozen Men's shooters."
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--since", default="2026-07-01")
    args = parser.parse_args()

    since = datetime.strptime(args.since, "%Y-%m-%d").date()

    db = Database(DATA / "mntrapteam.db")
    candidates = pool(db, args.season)

    print("MNTrapTeam ScoresR Recent Multi-Club Preview")
    print("============================================")
    print("READ ONLY — no database changes.")
    print(f"Candidate pool: {len(candidates)}")
    print(f"Scanning programs ending on/after: {since}")
    print()

    clubs = clubs_from_home()
    print(f"ScoresR clubs discovered from homepage: {len(clubs)}")
    print()

    total_programs = 0
    total_matches = 0
    unique = {}

    for ci, club in enumerate(clubs, 1):
        try:
            programs = programs_for_club(club)
        except Exception as exc:
            print(
                f"[{ci}/{len(clubs)}] {club.club_name}: "
                f"FAILED program list {type(exc).__name__}: {exc}"
            )
            continue

        recent = [
            p for p in programs
            if p.end_date is not None
            and p.end_date >= since
            and p.start_date is not None
            and p.start_date <= date.today()
        ]

        if not recent:
            continue

        print(
            f"[{ci}/{len(clubs)}] {club.club_name} | "
            f"recent programs={len(recent)}"
        )

        for program in recent:
            total_programs += 1
            print(f"  PROGRAM {program.program_id} | {program.label}")

            try:
                codes = event_codes(program)
            except Exception as exc:
                print(f"    FAILED event discovery: {type(exc).__name__}: {exc}")
                continue

            print(f"    score events={len(codes)}")

            for code, label in codes:
                try:
                    html = fetch_post(
                        DATA_URL,
                        {
                            "clubId": str(program.club_id),
                            "programId": str(program.program_id),
                            "viewWhatSelect": code,
                        },
                    )
                except Exception as exc:
                    print(f"      {code}: FAILED {type(exc).__name__}: {exc}")
                    continue

                text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)
                if "No Scoring Data Found" in text:
                    continue

                page_rows = rows(html)
                matches = []

                for row in page_rows:
                    for c, method in match_row(row, candidates):
                        matches.append((c, method, row))
                        unique[c.ata_number] = c

                if matches:
                    print(
                        f"      {code} {label}: "
                        f"rows={len(page_rows)} matches={len(matches)}"
                    )
                    for c, method, row in matches:
                        print(
                            f"        MATCH {c.ata_number} | "
                            f"{c.display_name} | via {method}"
                        )
                        print(f"          {row}")
                        total_matches += 1

        print()

    print("SUMMARY")
    print("-------")
    print(f"Recent ScoresR programs scanned: {total_programs}")
    print(f"Unique frozen Men's shooters found: {len(unique)}")
    print(f"Frozen-Men event-row matches found: {total_matches}")

    for ata in sorted(unique, key=lambda x: unique[x].display_name):
        c = unique[ata]
        print(f"{ata} | {c.display_name}")

    print()
    print("READ ONLY — no score rows were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
