from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .database import Database
from .paths import DATA
from .state_team_lock import ensure_schema as ensure_lock_schema


UA = "Mozilla/5.0 MNTrapTeam/5.0.0"
LIST_URL = "https://www.scoresr.com/regv2/PublicIfShowClubShoots.php"
DATA_URL = "https://www.scoresr.com/regv2/PublicIfShowData.php"


@dataclass(frozen=True)
class Candidate:
    ata_number: str
    display_name: str
    first_name: str
    last_name: str


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

        if first in tokens and last in tokens:
            named.append((c, "NAME"))

    if len(exact) == 1:
        return exact
    if len(named) == 1:
        return named
    return []


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


def rows(html: str):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tr in soup.find_all("tr"):
        cells = [" ".join(c.stripped_strings).strip() for c in tr.find_all(["th","td"])]
        if cells:
            out.append(cells)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Targeted ScoresR preview for a known completed program."
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--club-id", type=int, default=161)
    parser.add_argument("--program-id", type=int, default=4556)
    parser.add_argument("--club-name", default="Minneapolis Gun Club Inc")
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")
    candidates = pool(db, args.season)

    print("MNTrapTeam ScoresR Known-Program 68-Man Preview")
    print("===============================================")
    print("READ ONLY — no database changes.")
    print(f"Club: {args.club_name}")
    print(f"Program ID: {args.program_id}")
    print(f"Candidate pool: {len(candidates)}")
    print("Matching: full ATA when visible; otherwise unique first+last name.")
    print()

    codes = event_codes(args.club_id, args.program_id)
    print(f"Score events found: {len(codes)}")
    print()

    total = 0
    unique = {}

    for code, label in codes:
        html = fetch_post(
            DATA_URL,
            {
                "clubId": str(args.club_id),
                "programId": str(args.program_id),
                "viewWhatSelect": code,
            },
        )
        page_rows = rows(html)

        matches = []
        for row in page_rows:
            for c, method in match_row(row, candidates):
                matches.append((c, method, row))
                unique[c.ata_number] = c

        print(f"{code} {label}: rows={len(page_rows)} matches={len(matches)}")
        for c, method, row in matches:
            print(f"  MATCH {c.ata_number} | {c.display_name} | via {method}")
            print(f"    {row}")
            total += 1
        print()

    print("SUMMARY")
    print("-------")
    print(f"Unique frozen Men's shooters found: {len(unique)}")
    print(f"Frozen-Men event-row matches found: {total}")
    for ata in sorted(unique, key=lambda x: unique[x].display_name):
        c = unique[ata]
        print(f"{ata} | {c.display_name}")

    print()
    print("READ ONLY — no score rows were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
