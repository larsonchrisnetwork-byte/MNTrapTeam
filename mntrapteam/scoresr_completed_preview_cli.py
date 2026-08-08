from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .database import Database
from .paths import DATA
from .state_team_lock import ensure_schema as ensure_lock_schema


UA = "Mozilla/5.0 MNTrapTeam/4.9.7"
LIST_URL = "https://www.scoresr.com/regv2/PublicIfShowClubShoots.php"
DATA_URL = "https://www.scoresr.com/regv2/PublicIfShowData.php"


@dataclass(frozen=True)
class Candidate:
    ata_number: str
    display_name: str


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
        SELECT s.ata_number, s.display_name
        FROM state_team_qualification_lock l
        JOIN shooters s ON s.id=l.shooter_id
        WHERE l.season=? AND l.verified=1 AND l.state_team='MEN'
        ORDER BY s.display_name
        """,
        (season,),
    )
    return [
        Candidate(str(r["ata_number"]).strip(), str(r["display_name"]).strip())
        for r in rows if str(r["ata_number"] or "").strip()
    ]


def program_options(club_id: int, selected_program: int = 0):
    url = f"{LIST_URL}?clubId={club_id}&programId={selected_program}"
    html = fetch_get(url)
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", attrs={"name": "programId"})
    out = []
    if not select:
        return out
    for opt in select.find_all("option"):
        value = (opt.get("value") or "").strip()
        label = " ".join(opt.stripped_strings).strip()
        if value.isdigit() and label:
            out.append((int(value), label))
    return out


def event_codes(club_id: int, program_id: int):
    html = fetch_get(f"{LIST_URL}?clubId={club_id}&programId={program_id}")
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


def parse_end_date(label: str):
    m = re.match(r"\s*(\d{2})-(\d{2})-(\d{4})\s*-\s*(\d{2})-(\d{2})-(\d{4})", label)
    if not m:
        return None
    _, _, _, mm, dd, yyyy = map(int, m.groups())
    return date(yyyy, mm, dd)


def table_rows(html: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = [" ".join(c.stripped_strings).strip() for c in tr.find_all(["th","td"])]
        if cells:
            rows.append(cells)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--club-id", type=int, default=161)
    parser.add_argument("--club-name", default="Minneapolis Gun Club Inc")
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")
    pool = candidate_pool(db, args.season)
    by_ata = {c.ata_number: c for c in pool}

    print("MNTrapTeam ScoresR Completed-Shoot 68-Man Preview")
    print("=================================================")
    print("READ ONLY — no database changes.")
    print(f"Club: {args.club_name}")
    print(f"Candidate pool: {len(pool)}")
    print()

    programs = program_options(args.club_id)
    programs = [(pid, label) for pid, label in programs if str(args.season) in label]

    print(f"2026 programs found: {len(programs)}")
    total_matches = 0

    for pid, label in programs:
        end = parse_end_date(label)
        status = "FUTURE" if end and end > date.today() else "COMPLETED/CURRENT"
        print()
        print(f"PROGRAM {pid} | {status} | {label}")

        if end and end > date.today():
            print("  Skipping future shoot.")
            continue

        codes = event_codes(args.club_id, pid)
        print(f"  Score events found: {len(codes)}")

        for code, event_label in codes:
            html = fetch_post(
                DATA_URL,
                {
                    "clubId": str(args.club_id),
                    "programId": str(pid),
                    "viewWhatSelect": code,
                },
            )
            text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)
            if "No Scoring Data Found" in text:
                print(f"    {code} {event_label}: no scoring data")
                continue

            rows = table_rows(html)
            matches = []
            for row in rows:
                joined = " | ".join(row)
                for ata, candidate in by_ata.items():
                    if ata in joined:
                        matches.append((candidate, row))

            print(f"    {code} {event_label}: rows={len(rows)} matches={len(matches)}")
            for candidate, row in matches:
                print(f"      MATCH {candidate.ata_number} | {candidate.display_name}")
                print(f"        {row}")
                total_matches += 1

    print()
    print("SUMMARY")
    print("-------")
    print(f"Frozen-Men event-row matches found: {total_matches}")
    print("READ ONLY — no score rows were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
