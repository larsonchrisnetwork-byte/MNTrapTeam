from __future__ import annotations

import argparse
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .database import Database
from .official_baseline import ensure_schema as ensure_baseline_schema
from .paths import DATA
from .state_team_lock import ensure_schema as ensure_lock_schema


UA = "Mozilla/5.0 MNTrapTeam/4.9.6"
POST_URL = "https://www.scoresr.com/regv2/PublicIfShowData.php"


@dataclass(frozen=True)
class Candidate:
    shooter_id: int
    ata_number: str
    display_name: str


def candidates(db: Database, season: int) -> list[Candidate]:
    ensure_baseline_schema(db)
    ensure_lock_schema(db)

    rows = db.query(
        """
        SELECT s.id AS shooter_id, s.ata_number, s.display_name
        FROM state_team_qualification_lock l
        JOIN shooters s ON s.id=l.shooter_id
        WHERE l.season=?
          AND l.verified=1
          AND l.state_team='MEN'
        ORDER BY s.display_name
        """,
        (season,),
    )

    return [
        Candidate(
            shooter_id=int(r["shooter_id"]),
            ata_number=str(r["ata_number"] or "").strip(),
            display_name=str(r["display_name"] or "").strip(),
        )
        for r in rows
        if str(r["ata_number"] or "").strip()
    ]


def post_score_view(club_id: int, program_id: int, view_code: str, timeout: int = 15) -> str:
    payload = urlencode(
        {
            "clubId": str(club_id),
            "programId": str(program_id),
            "viewWhatSelect": view_code,
        }
    ).encode("utf-8")

    req = Request(
        POST_URL,
        data=payload,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Referer": (
                "https://www.scoresr.com/regv2/PublicIfShowClubShoots.php"
                f"?clubId={club_id}&programId={program_id}"
            ),
        },
        method="POST",
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def tables(html: str) -> list[list[list[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    result = []
    for table in soup.find_all("table"):
        parsed = []
        for tr in table.find_all("tr"):
            cells = [
                " ".join(c.stripped_strings).strip()
                for c in tr.find_all(["th", "td"])
            ]
            if cells:
                parsed.append(cells)
        if parsed:
            result.append(parsed)
    return result


def candidate_matches(html: str, pool: list[Candidate]) -> list[tuple[Candidate, list[str]]]:
    page_tables = tables(html)
    matches = []

    for candidate in pool:
        ata = candidate.ata_number
        for table in page_tables:
            for row in table:
                joined = " | ".join(row)
                if ata in joined:
                    matches.append((candidate, row))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read ScoresR event score views and show frozen Men's candidates."
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--club-id", type=int, default=161)
    parser.add_argument("--program-id", type=int, default=4705)
    parser.add_argument(
        "--events",
        default="s17154,s17155,s17156",
        help="Comma-separated ScoresR score view codes.",
    )
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")
    pool = candidates(db, args.season)

    print("MNTrapTeam ScoresR 68-Man Event Score Preview")
    print("=============================================")
    print("READ ONLY — no database changes.")
    print(f"Candidate pool: {len(pool)}")
    print(f"Club ID: {args.club_id}")
    print(f"Program ID: {args.program_id}")
    print()

    total_matches = 0

    for code in [x.strip() for x in args.events.split(",") if x.strip()]:
        print(f"VIEW {code}")
        print("-" * (5 + len(code)))

        try:
            html = post_score_view(args.club_id, args.program_id, code)
        except Exception as exc:
            print(f"FAILED: {type(exc).__name__}: {exc}")
            print()
            continue

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text_start = " ".join(soup.stripped_strings)[:500]

        print(f"HTML bytes: {len(html.encode('utf-8'))}")
        print(f"Title: {title!r}")
        print(f"Text start: {text_start}")
        print()

        page_tables = tables(html)
        print(f"Tables found: {len(page_tables)}")
        for i, table in enumerate(page_tables[:3], 1):
            print(f"  Table {i} rows: {len(table)}")
            for row in table[:5]:
                print(f"    {row}")

        matches = candidate_matches(html, pool)
        print()
        print(f"Frozen Men's matches: {len(matches)}")

        for candidate, row in matches:
            print(f"  MATCH {candidate.ata_number} | {candidate.display_name}")
            print(f"    {row}")
            total_matches += 1

        print()
        print("=" * 72)
        print()

    print("SUMMARY")
    print("-------")
    print(f"Total frozen-Men event-row matches: {total_matches}")
    print("READ ONLY — no score rows were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
