from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .database import Database
from .official_baseline import ensure_schema as ensure_baseline_schema
from .paths import DATA
from .recent_score_scout_cli import _match
from .state_team_lock import ensure_schema as ensure_lock_schema


BASE = "https://www.shootatazone.com/central/"
SEASON = 2026

EVENTS = {
    1: ("2026-07-24", "singles", 100, "CLASS SINGLES"),
    2: ("2026-07-24", "handicap", 100, "PRELIMINARY HANDICAP"),
    3: ("2026-07-24", "doubles", 100, "CLASS DOUBLES"),
    4: ("2026-07-25", "singles", 200, "SINGLES CHAMPIONSHIP"),
    5: ("2026-07-26", "doubles", 100, "DOUBLES CHAMPIONSHIP"),
    6: ("2026-07-26", "handicap", 100, "HANDICAP CHAMPIONSHIP"),
}


@dataclass(frozen=True)
class Candidate:
    shooter_id: int
    ata_number: str
    display_name: str
    first_name: str
    last_name: str
    cutoff: str


def fetch(url: str, timeout: int = 10) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MNTrapTeam/4.7.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def candidate_pool(db: Database, season: int) -> list[Candidate]:
    ensure_baseline_schema(db)
    ensure_lock_schema(db)

    rows = db.query(
        """
        SELECT
            l.shooter_id,
            s.ata_number,
            s.display_name,
            s.first_name,
            s.last_name,
            b.official_through_date
        FROM state_team_qualification_lock l
        JOIN shooters s ON s.id=l.shooter_id
        JOIN official_season_baselines b
          ON b.shooter_id=l.shooter_id
         AND b.season=l.season
        WHERE l.season=?
          AND l.verified=1
          AND l.state_team='MEN'
          AND trim(COALESCE(b.official_through_date,''))<>''
        ORDER BY s.display_name
        """,
        (season,),
    )

    return [
        Candidate(
            shooter_id=int(r["shooter_id"]),
            ata_number=str(r["ata_number"] or ""),
            display_name=str(r["display_name"] or ""),
            first_name=str(r["first_name"] or ""),
            last_name=str(r["last_name"] or ""),
            cutoff=str(r["official_through_date"] or ""),
        )
        for r in rows
    ]


def _total_pages(html: str) -> int:
    text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)
    match = re.search(
        r"SCORE\(S\)\s+\d+\s+TO\s+\d+\s+OF\s+(\d+)\s+TOTAL SCORES FOUND",
        text,
        re.IGNORECASE,
    )
    if not match:
        return 1
    total = int(match.group(1))
    return max(1, math.ceil(total / 100))


def _score_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    result = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        header_idx = None
        headers = None
        for i, tr in enumerate(rows[:8]):
            cells = [
                " ".join(cell.stripped_strings).strip()
                for cell in tr.find_all(["th", "td"])
            ]
            upper = [c.upper() for c in cells]
            if "CLUB" in upper and "NAME" in upper and "ST" in upper and "TOTAL" in upper:
                header_idx = i
                headers = upper
                break

        if header_idx is None:
            continue

        club_idx = headers.index("CLUB")
        name_idx = headers.index("NAME")
        state_idx = headers.index("ST")
        total_idx = headers.index("TOTAL")

        for tr in rows[header_idx + 1:]:
            cells = [
                " ".join(cell.stripped_strings).strip()
                for cell in tr.find_all(["td", "th"])
            ]
            needed = max(club_idx, name_idx, state_idx, total_idx)
            if len(cells) <= needed:
                continue

            club = cells[club_idx].strip()
            name = cells[name_idx].strip()
            state = cells[state_idx].strip().upper()
            total_text = cells[total_idx].strip()

            m = re.search(r"\b(\d{1,3})\b", total_text)
            if not club or not name or not m:
                continue

            result.append(
                {
                    "club": club,
                    "name": name,
                    "state": state,
                    "hits": int(m.group(1)),
                }
            )

    return result


def _event_rows(event_id: int) -> list[dict]:
    first_url = f"{BASE}reports.cfm?sorteventid={event_id}"
    first_html = fetch(first_url)
    pages = _total_pages(first_html)

    rows = _score_rows(first_html)

    for page in range(2, pages + 1):
        print(f"    page {page}/{pages}", flush=True)
        url = (
            f"{BASE}reports.cfm?"
            f"PageNum_Recordset1={page}&sorteventid={event_id}"
        )
        rows.extend(_score_rows(fetch(url)))

    return rows


def _shoot_name(club: str) -> str:
    return f"2026 ATA Central Zone - {club}"


def _source_url(event_id: int) -> str:
    return f"{BASE}reports.cfm?sorteventid={event_id}"


def _stored_event_name(event_id: int) -> str:
    return f"E{event_id} {EVENTS[event_id][3]}"


def _in_state(club: str) -> int:
    return 1 if re.search(r"\(\s*MN\s*\)\s*$", club.upper()) else 0


def _existing(
    db: Database,
    shooter_id: int,
    club: str,
    event_id: int,
    discipline: str,
) -> bool:
    shoot_name = _shoot_name(club)
    event_name = _stored_event_name(event_id)

    rows = db.query(
        """
        SELECT sc.id
        FROM scores sc
        LEFT JOIN shoots sh ON sh.id=sc.shoot_id
        WHERE sc.shooter_id=?
          AND upper(COALESCE(sh.name,''))=upper(?)
          AND upper(COALESCE(sc.event_name,''))=upper(?)
          AND lower(COALESCE(sc.discipline,''))=lower(?)
        LIMIT 1
        """,
        (shooter_id, shoot_name, event_name, discipline),
    )
    return bool(rows)


def _ensure_shoot(db: Database, club: str) -> int:
    name = _shoot_name(club)
    rows = db.query(
        "SELECT id FROM shoots WHERE name=? ORDER BY id LIMIT 1",
        (name,),
    )
    if rows:
        return int(rows[0]["id"])

    return int(
        db.execute(
            """
            INSERT INTO shoots(
                name,club,city,state,start_date,end_date,source_type,source_url
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                name,
                club,
                "",
                "MN" if _in_state(club) else "",
                "2026-07-24",
                "2026-07-26",
                "ATA Central Zone web",
                BASE,
            ),
        )
    )


def discover(db: Database, season: int) -> dict:
    candidates = candidate_pool(db, season)
    if not candidates:
        raise RuntimeError("No baseline-ready locked Men's candidates found")

    found = []
    needs_reconciliation = []
    ambiguous = []
    counts = {}

    print(f"Candidate pool loaded: {len(candidates)}")

    for event_id in range(1, 7):
        event_date, discipline, targets, label = EVENTS[event_id]
        print(
            f"Scanning Central Zone E{event_id} {label} "
            f"({event_date})...",
            flush=True,
        )
        rows = _event_rows(event_id)
        counts[event_id] = len(rows)
        print(f"  score rows read: {len(rows)}", flush=True)

        for row in rows:
            matches = _match(candidates, row["name"], row["state"])
            if not matches:
                continue
            if len(matches) != 1:
                ambiguous.append(
                    {
                        "event_id": event_id,
                        "row": row,
                        "matches": [c.display_name for c in matches],
                    }
                )
                continue

            candidate = matches[0]

            if _existing(
                db,
                candidate.shooter_id,
                row["club"],
                event_id,
                discipline,
            ):
                continue

            item = {
                "candidate": candidate,
                "event_id": event_id,
                "event_date": event_date,
                "discipline": discipline,
                "targets": targets,
                "label": label,
                "row": row,
            }

            if event_date <= candidate.cutoff:
                # A later MyATA score does NOT prove this older event is already
                # official. Keep it visible for exact-shoot reconciliation.
                needs_reconciliation.append(item)
            else:
                found.append(item)

    return {
        "candidates": candidates,
        "found": found,
        "needs_reconciliation": needs_reconciliation,
        "ambiguous": ambiguous,
        "counts": counts,
    }


def print_result(result: dict) -> None:
    print()
    print("MNTrapTeam ATA Central Zone — Men's Live Overlay")
    print("================================================")
    print(f"Men's HAA candidates: {len(result['candidates'])}")
    print(f"New Central Zone score rows found: {len(result['found'])}")
    print(
        "Older-than-latest-MyATA rows needing exact reconciliation: "
        f"{len(result['needs_reconciliation'])}"
    )
    print(f"Ambiguous rows held: {len(result['ambiguous'])}")
    print()

    grouped = {}
    for item in result["found"]:
        name = item["candidate"].display_name
        grouped.setdefault(name, []).append(item)

    for name in sorted(grouped):
        candidate = grouped[name][0]["candidate"]
        print(f"{name} | MyATA through {candidate.cutoff}")
        for item in grouped[name]:
            row = item["row"]
            state_flag = "MN TARGETS" if _in_state(row["club"]) else "OUT OF STATE"
            print(
                f"  + {item['event_date']} | {row['club']} | "
                f"E{item['event_id']} {item['discipline']} "
                f"{row['hits']}/{item['targets']} | {state_flag}"
            )

    if result.get("needs_reconciliation"):
        print()
        print("NEEDS EXACT MYATA RECONCILIATION")
        print("-------------------------------")
        grouped_recon = {}
        for item in result["needs_reconciliation"]:
            grouped_recon.setdefault(item["candidate"].display_name, []).append(item)

        for name in sorted(grouped_recon):
            candidate = grouped_recon[name][0]["candidate"]
            print(f"{name} | MyATA latest date {candidate.cutoff}")
            for item in grouped_recon[name]:
                row = item["row"]
                state_flag = "MN TARGETS" if _in_state(row["club"]) else "OUT OF STATE"
                print(
                    f"  ? {item['event_date']} | {row['club']} | "
                    f"E{item['event_id']} {item['discipline']} "
                    f"{row['hits']}/{item['targets']} | {state_flag}"
                )

    if result["ambiguous"]:
        print()
        print("AMBIGUOUS — NOT IMPORTED")
        print("------------------------")
        for item in result["ambiguous"]:
            print(
                f"E{item['event_id']} | {item['row']['club']} | "
                f"{item['row']['name']} -> {', '.join(item['matches'])}"
            )


def write_found(db: Database, result: dict) -> int:
    written = 0

    for item in result["found"]:
        candidate = item["candidate"]
        row = item["row"]
        event_id = item["event_id"]

        shoot_id = _ensure_shoot(db, row["club"])

        db.execute(
            """
            INSERT INTO scores(
                shooter_id,shoot_id,event_date,event_name,discipline,
                targets,hits,in_state,club_key,source,official,raw_name
            ) VALUES(?,?,?,?,?,?,?,?,?,?,0,?)
            """,
            (
                candidate.shooter_id,
                shoot_id,
                item["event_date"],
                _stored_event_name(event_id),
                item["discipline"],
                item["targets"],
                row["hits"],
                _in_state(row["club"]),
                row["club"],
                "ATA Central Zone web",
                row["name"],
            ),
        )
        written += 1

    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find/import 2026 ATA Central Zone scores newer than each locked "
            "Men's candidate's MyATA official-through date."
        )
    )
    parser.add_argument(
        "action",
        choices=("preview", "write"),
        nargs="?",
        default="preview",
    )
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")
    result = discover(db, args.season)
    print_result(result)

    if args.action == "preview":
        print()
        print("PREVIEW ONLY — no database changes made.")
        return 0

    written = write_found(db, result)
    print()
    print(f"Central Zone provisional rows written: {written}")
    print("Official MyATA season_stats were NOT modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
