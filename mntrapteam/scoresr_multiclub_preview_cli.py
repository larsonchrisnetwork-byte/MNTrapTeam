from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .database import Database
from .paths import DATA
from .state_team_lock import ensure_schema as ensure_lock_schema


UA = "Mozilla/5.0 MNTrapTeam/4.9.9"
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
class Program:
    club_id: int
    program_id: int
    club_name: str


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


def candidate_pool(db: Database, season: int) -> list[Candidate]:
    ensure_lock_schema(db)
    rows = db.query(
        """
        SELECT
            s.ata_number,
            s.display_name,
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
        for r in rows
        if str(r["ata_number"] or "").strip()
    ]


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.upper().replace(",", " ").replace(".", " ")
    value = re.sub(r"[^A-Z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _name_tokens(value: str) -> list[str]:
    return [t for t in _norm(value).split() if t]


def _row_matches_candidate(row: list[str], candidate: Candidate) -> tuple[bool, str]:
    joined = " | ".join(row)
    joined_norm = _norm(joined)

    # Strongest match: complete ATA number visible.
    if candidate.ata_number and candidate.ata_number in joined:
        return True, "ATA"

    first = _norm(candidate.first_name)
    last = _norm(candidate.last_name)

    if not first or not last:
        # Fallback to first and last tokens from display name.
        toks = _name_tokens(candidate.display_name)
        if len(toks) >= 2:
            first, last = toks[0], toks[-1]

    if not first or not last:
        return False, ""

    # Conservative masked-ATA fallback: both first and last names must appear
    # as standalone tokens somewhere in the row.
    row_tokens = set(_name_tokens(joined_norm))
    if first in row_tokens and last in row_tokens:
        return True, "NAME"

    return False, ""


def _unique_candidate_matches(row: list[str], pool: list[Candidate]):
    raw = []
    for candidate in pool:
        matched, method = _row_matches_candidate(row, candidate)
        if matched:
            raw.append((candidate, method))

    # Exact ATA always wins if present.
    ata_matches = [(c, m) for c, m in raw if m == "ATA"]
    if len(ata_matches) == 1:
        return ata_matches

    # For masked ATA rows, only accept a single unique name match.
    name_matches = [(c, m) for c, m in raw if m == "NAME"]
    unique = {}
    for c, m in name_matches:
        unique[c.ata_number] = (c, m)
    if len(unique) == 1:
        return list(unique.values())

    return []


def public_programs_from_home() -> list[Program]:
    html = fetch_get(HOME)
    soup = BeautifulSoup(html, "html.parser")
    found = {}

    for a in soup.find_all("a", href=True):
        href = urljoin(HOME, a["href"])
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)

        club_id = None
        program_id = None
        club_name = ""

        if "PublicIfShowShootProgram.php" in parsed.path:
            club_vals = qs.get("clubId", [])
            prog_vals = qs.get("programId", [])
            name_vals = qs.get("clubName", [])
            if club_vals and prog_vals:
                club_id = club_vals[0]
                program_id = prog_vals[0]
                club_name = name_vals[0] if name_vals else ""

        elif "ShootICMain.php" in parsed.path:
            club_vals = qs.get("forwardClubId", [])
            prog_vals = qs.get("forwardProgramId", [])
            name_vals = qs.get("forwardClubName", [])
            if club_vals and prog_vals:
                club_id = club_vals[0]
                program_id = prog_vals[0]
                club_name = name_vals[0] if name_vals else ""

        if not club_id or not program_id:
            continue
        if not str(club_id).isdigit() or not str(program_id).isdigit():
            continue

        club_name = club_name.replace("+", " ").strip() or f"Club {club_id}"
        key = (int(club_id), int(program_id))
        found[key] = Program(int(club_id), int(program_id), club_name)

    return sorted(found.values(), key=lambda p: (p.club_name, p.program_id))


def event_codes(program: Program):
    html = fetch_get(
        f"{LIST_URL}?clubId={program.club_id}&programId={program.program_id}"
    )
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", attrs={"name": "viewWhatSelect"})
    result = []
    if not select:
        return result

    for opt in select.find_all("option"):
        value = (opt.get("value") or "").strip()
        label = " ".join(opt.stripped_strings).strip()
        if re.fullmatch(r"s\d+", value):
            result.append((value, label))
    return result


def table_rows(html: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = [
            " ".join(c.stripped_strings).strip()
            for c in tr.find_all(["th", "td"])
        ]
        if cells:
            rows.append(cells)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan all currently exposed ScoresR programs for the frozen Men's pool."
    )
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")
    pool = candidate_pool(db, args.season)

    print("MNTrapTeam ScoresR Multi-Club 68-Man Preview")
    print("============================================")
    print("READ ONLY — no database changes.")
    print(f"Candidate pool: {len(pool)}")
    print("Matching: full ATA when visible; otherwise unique first+last name.")
    print()

    programs = public_programs_from_home()
    print(f"Public ScoresR programs discovered from homepage: {len(programs)}")
    print()

    unique_matches = {}
    event_match_count = 0

    for index, program in enumerate(programs, 1):
        print(
            f"[{index}/{len(programs)}] "
            f"{program.club_name} | club {program.club_id} | program {program.program_id}"
        )

        try:
            codes = event_codes(program)
        except Exception as exc:
            print(f"  FAILED event discovery: {type(exc).__name__}: {exc}")
            continue

        print(f"  score events: {len(codes)}")

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
                print(f"    {code}: FAILED {type(exc).__name__}: {exc}")
                continue

            text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)
            if "No Scoring Data Found" in text:
                print(f"    {code} {label}: no scoring data")
                continue

            rows = table_rows(html)
            matches = []

            for row in rows:
                for candidate, method in _unique_candidate_matches(row, pool):
                    matches.append((candidate, method, row))
                    unique_matches.setdefault(candidate.ata_number, candidate)

            print(
                f"    {code} {label}: rows={len(rows)} "
                f"frozen-Men matches={len(matches)}"
            )

            for candidate, method, row in matches:
                print(
                    f"      MATCH {candidate.ata_number} | "
                    f"{candidate.display_name} | via {method}"
                )
                print(f"        {row}")
                event_match_count += 1

        print()

    print("SUMMARY")
    print("-------")
    print(f"ScoresR programs scanned: {len(programs)}")
    print(f"Unique frozen Men's shooters found: {len(unique_matches)}")
    print(f"Frozen-Men event-row matches found: {event_match_count}")

    for ata in sorted(unique_matches, key=lambda x: unique_matches[x].display_name):
        c = unique_matches[ata]
        print(f"{ata} | {c.display_name}")

    print()
    print("READ ONLY — no score rows were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
