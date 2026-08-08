from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .database import Database
from .official_baseline import ensure_schema as ensure_baseline_schema
from .paths import DATA
from .state_team_lock import ensure_schema as ensure_lock_schema


UA = "Mozilla/5.0 MNTrapTeam/4.9.3"


@dataclass(frozen=True)
class Candidate:
    shooter_id: int
    ata_number: str
    display_name: str


def fetch(url: str, timeout: int = 12) -> tuple[str, str]:
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.geturl(), response.read().decode("utf-8", errors="replace")


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


def same_program(url: str, club_id: int, program_id: int) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"www.scoresr.com", "scoresr.com"}:
        return False

    qs = parse_qs(parsed.query)
    club_values = qs.get("clubId", []) + qs.get("forwardClubId", [])
    program_values = qs.get("p", []) + qs.get("programId", []) + qs.get("forwardProgramId", [])

    if club_values and str(club_id) not in club_values:
        return False
    if program_values and str(program_id) not in program_values:
        return False

    path = parsed.path.lower()
    return (
        "/regv2/" in path
        and any(
            key in path
            for key in (
                "publicviewshoot",
                "shootic",
                "score",
                "result",
                "report",
                "event",
                "rolling",
                "high",
            )
        )
    )


def row_texts(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = [" ".join(c.stripped_strings).strip() for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(" | ".join(cells))
    return rows


def relevant_links(html: str, base_url: str, club_id: int, program_id: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        text = " ".join(a.stripped_strings).strip()
        blob = f"{text} {href}".upper()

        if not any(
            key in blob
            for key in ("SCORE", "RESULT", "REPORT", "EVENT", "HIGH", "ROLLING", "VIEW")
        ):
            continue

        if not same_program(href, club_id, program_id):
            continue

        if href in seen:
            continue
        seen.add(href)
        links.append(href)

    return links


def scan_program(db: Database, season: int, club_id: int, program_id: int, club_name: str) -> int:
    pool = candidates(db, season)
    by_ata = {c.ata_number: c for c in pool}

    club_name_q = club_name.replace(" ", "+")
    start = (
        "https://www.scoresr.com/regv2/PublicViewShoot.php"
        f"?clubId={club_id}&p={program_id}&name={club_name_q}"
    )

    print("MNTrapTeam ScoresR 68-Man Public Score Scan")
    print("===========================================")
    print("READ ONLY — no database changes.")
    print(f"Candidate pool: {len(pool)}")
    print(f"Club: {club_name}")
    print(f"Club ID: {club_id}")
    print(f"Program ID: {program_id}")
    print()

    queue = deque([(start, 0)])
    visited = set()
    matches = []
    max_depth = 2
    max_pages = 40

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        print(f"[{len(visited)}] depth={depth} {url}", flush=True)

        try:
            final_url, html = fetch(url)
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            continue

        page_rows = row_texts(html)
        page_blob = html.upper()

        found_here = 0
        for ata, candidate in by_ata.items():
            if ata not in page_blob:
                continue

            evidence = [row for row in page_rows if ata in row]
            if not evidence:
                evidence = [f"ATA {ata} appears in page HTML"]

            for row in evidence:
                matches.append((candidate, final_url, row))
                print(f"  MATCH {ata} | {candidate.display_name}")
                print(f"    {row[:1000]}")
                found_here += 1

        links = relevant_links(html, final_url, club_id, program_id)
        print(f"  candidate rows matched: {found_here}")
        print(f"  same-program report links found: {len(links)}")

        if depth < max_depth:
            for link in links:
                if link not in visited:
                    queue.append((link, depth + 1))

    print()
    print("SUMMARY")
    print("-------")
    unique = {}
    for candidate, url, row in matches:
        unique.setdefault(candidate.ata_number, candidate)

    print(f"Public ScoresR pages inspected: {len(visited)}")
    print(f"Frozen Men's candidates found: {len(unique)}")

    for ata in sorted(unique, key=lambda x: unique[x].display_name):
        c = unique[ata]
        print(f"{ata} | {c.display_name}")

    print()
    print("READ ONLY — no score rows were written.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search a ScoresR program for the frozen Men's candidate pool."
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--club-id", type=int, default=161)
    parser.add_argument("--program-id", type=int, default=4705)
    parser.add_argument("--club-name", default="Minneapolis Gun Club Inc")
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")
    return scan_program(
        db,
        args.season,
        args.club_id,
        args.program_id,
        args.club_name,
    )


if __name__ == "__main__":
    raise SystemExit(main())
