from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .database import Database
from .official_baseline import ensure_schema as ensure_baseline_schema
from .paths import DATA
from .shootscoreboard_web import BASE_URL, fetch_text, parse_shoot_header
from .state_team_lock import ensure_schema as ensure_lock_schema


@dataclass(frozen=True)
class Candidate:
    shooter_id: int
    ata_number: str
    display_name: str
    first_name: str
    last_name: str
    cutoff: str


@dataclass(frozen=True)
class ScoutEvent:
    event_id: int
    name: str
    discipline: str
    entries: list[dict]


@dataclass(frozen=True)
class ScoutShoot:
    shoot_id: int
    name: str
    start_date: str
    end_date: str
    source_url: str
    events: list[ScoutEvent]


_EVENT_CODE = {"S": "singles", "H": "handicap", "D": "doubles"}


def _event_specs_from_entries(html: str) -> list[tuple[int, str]]:
    """Read actual ATA event IDs from ShootScoreBoard Event Entries page."""
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.stripped_strings).upper()
    found = {}
    for match in re.finditer(r"\bE(\d+)\s*\(\s*([SHD])\s*\)", text):
        event_id = int(match.group(1))
        found[event_id] = _EVENT_CODE[match.group(2)]
    return sorted(found.items())


def _numeric_parts(value: str) -> list[int]:
    return [int(x) for x in re.findall(r"\b\d{1,3}\b", str(value or ""))]


def _targets_from_scores(score_text: str, discipline: str, hits: int) -> int:
    parts = _numeric_parts(score_text)
    if discipline == "doubles":
        if parts:
            return len(parts) * 50
    else:
        if parts:
            return len(parts) * 25

    # Conservative fallback for unusual table formatting.
    if hits > 100:
        return 200
    return 100


def _parse_report_relaxed(
    html: str,
    event_id: int,
    discipline: str,
) -> ScoutEvent:
    """Parse all score tables on a ShootScoreBoard report page."""
    soup = BeautifulSoup(html, "html.parser")
    page_text = " ".join(soup.stripped_strings)

    title_match = re.search(
        rf"EVENT\s+{event_id}\s*-\s*(.+?)(?:\s+\d+\s+ENTRIES\b|\s+NAME\b)",
        page_text,
        re.IGNORECASE,
    )
    event_name = (
        title_match.group(1).strip()
        if title_match
        else f"EVENT {event_id}"
    )

    entries = []
    seen = set()

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        header_index = None
        header_cells = None

        for idx, tr in enumerate(rows[:5]):
            cells = [
                " ".join(td.stripped_strings).strip()
                for td in tr.find_all(["th", "td"])
            ]
            upper = [c.upper() for c in cells]
            if "NAME" in upper and "STATE" in upper and "TOTAL" in upper:
                header_index = idx
                header_cells = upper
                break

        if header_index is None or not header_cells:
            continue

        try:
            name_idx = header_cells.index("NAME")
            state_idx = header_cells.index("STATE")
            total_idx = header_cells.index("TOTAL")
        except ValueError:
            continue

        scores_idx = None
        for label in ("SCORES", "SCORE"):
            if label in header_cells:
                scores_idx = header_cells.index(label)
                break

        for tr in rows[header_index + 1:]:
            cells = [
                " ".join(td.stripped_strings).strip()
                for td in tr.find_all(["td", "th"])
            ]
            if len(cells) <= max(name_idx, state_idx, total_idx):
                continue

            name = cells[name_idx].strip()
            state = cells[state_idx].strip().upper()

            if not name or not re.fullmatch(r"[A-Z]{2}", state):
                continue

            total_cell = cells[total_idx].strip()
            total_match = re.search(r"\b(\d{1,3})\b", total_cell)
            if not total_match:
                continue
            hits = int(total_match.group(1))

            score_text = ""
            if scores_idx is not None and scores_idx < len(cells):
                score_text = cells[scores_idx]
            else:
                scored = []
                for cell in cells:
                    parts = _numeric_parts(cell)
                    if len(parts) >= 2 and "-" in cell:
                        scored.append((len(parts), cell))
                if scored:
                    score_text = max(scored, key=lambda item: item[0])[1]

            targets = _targets_from_scores(score_text, discipline, hits)
            if hits > targets:
                targets = 200 if hits <= 200 else hits

            key = (name, state, targets, hits)
            if key in seen:
                continue
            seen.add(key)

            entries.append(
                {
                    "name": name,
                    "state": state,
                    "targets": targets,
                    "hits": hits,
                }
            )

    if not entries:
        raise ValueError(f"Event {event_id}: no score rows parsed")

    return ScoutEvent(event_id, event_name, discipline, entries)


def _load_shoot_from_entries(shoot_id: int, timeout: int = 5) -> ScoutShoot:
    menu_url = f"{BASE_URL}menu.cfm?shootid={shoot_id}"
    menu_html = fetch_text(menu_url, timeout=timeout)
    name, start_date, end_date = parse_shoot_header(menu_html, shoot_id)

    entries_url = f"{BASE_URL}entrys.cfm?shootid={shoot_id}"
    entries_html = fetch_text(entries_url, timeout=timeout)
    specs = _event_specs_from_entries(entries_html)
    if not specs:
        raise ValueError("No scored S/H/D events listed on Event Entries page")

    events = []
    for event_id, discipline in specs:
        report_url = f"{BASE_URL}reports.cfm?shootid={shoot_id}&sorteventid={event_id}"
        try:
            report_html = fetch_text(report_url, timeout=timeout)
            event = _parse_report_relaxed(report_html, event_id, discipline)
        except KeyboardInterrupt:
            raise
        except Exception:
            continue
        events.append(event)

    if not events:
        raise ValueError("No supported score reports could be parsed")

    return ScoutShoot(
        shoot_id=shoot_id,
        name=name,
        start_date=start_date,
        end_date=end_date,
        source_url=menu_url,
        events=events,
    )


def _compact_name(value: str) -> str:
    text = re.sub(r"[^A-Z0-9 ]+", " ", str(value or "").upper())
    return " ".join(t for t in text.split() if t)


def _identity_tokens(value: str) -> tuple[tuple[str, ...], str]:
    """
    Return significant name tokens independent of FIRST/LAST display order.

    Middle initials are intentionally ignored because ShootScoreBoard commonly
    prints LAST FIRST M while MyATA/database display names are FIRST M LAST.
    JR/SR suffixes are preserved so Joel Johnson Jr cannot silently match a
    different Joel Johnson record.
    """
    tokens = _compact_name(value).split()
    suffix = ""
    if tokens and tokens[-1] in {"JR", "SR", "II", "III", "IV"}:
        suffix = tokens.pop()

    significant = tuple(sorted(t for t in tokens if len(t) > 1))
    return significant, suffix


def _identity_key(value: str) -> tuple[tuple[str, ...], str]:
    return _identity_tokens(value)


def _name_keys(display_name: str, first_name: str, last_name: str) -> set[str]:
    keys = set()
    display = _compact_name(display_name)
    first = _compact_name(first_name)
    last = _compact_name(last_name)
    if display:
        keys.add(display)
        parts = display.split()
        if len(parts) >= 2:
            keys.add(" ".join(reversed(parts)))
            stripped = [p for p in parts if len(p) > 1 or p in {"JR", "SR"}]
            if len(stripped) >= 2:
                keys.add(" ".join(stripped))
                keys.add(" ".join(reversed(stripped)))
    if first and last:
        keys.add(f"{first} {last}")
        keys.add(f"{last} {first}")
    return keys


def _candidate_pool(db: Database, season: int) -> list[Candidate]:
    ensure_baseline_schema(db)
    ensure_lock_schema(db)
    rows = db.query(
        """
        SELECT l.shooter_id,s.ata_number,s.display_name,s.first_name,s.last_name,
               b.official_through_date
        FROM state_team_qualification_lock l
        JOIN shooters s ON s.id=l.shooter_id
        JOIN official_season_baselines b
          ON b.shooter_id=l.shooter_id AND b.season=l.season
        WHERE l.season=? AND l.verified=1 AND l.state_team='MEN'
          AND trim(COALESCE(b.official_through_date,''))<>''
        ORDER BY s.display_name
        """,
        (season,),
    )
    return [
        Candidate(
            int(r["shooter_id"]),
            str(r["ata_number"] or ""),
            str(r["display_name"] or ""),
            str(r["first_name"] or ""),
            str(r["last_name"] or ""),
            str(r["official_through_date"] or ""),
        )
        for r in rows
    ]


def _parse_scan_range(value: str) -> range:
    match = re.fullmatch(r"\s*(\d+)\s*[:-]\s*(\d+)\s*", value or "")
    if not match:
        raise argparse.ArgumentTypeError("Use START:END, e.g. 2000:2200")
    start, end = map(int, match.groups())
    if start <= 0 or end < start:
        raise argparse.ArgumentTypeError("Invalid shoot-ID range")
    return range(start, end + 1)


def _home_shoot_ids() -> set[int]:
    ids = set()
    try:
        soup = BeautifulSoup(fetch_text(BASE_URL), "html.parser")
    except Exception:
        return ids
    for anchor in soup.find_all("a", href=True):
        parsed = urlparse(anchor["href"])
        shootid = parse_qs(parsed.query).get("shootid", [""])[0]
        if shootid.isdigit():
            ids.add(int(shootid))
    return ids


def _recent_ids(candidates: list[Candidate], scan_range: range) -> list[int]:
    earliest = min(c.cutoff for c in candidates)
    today = date.today().isoformat()
    ids = sorted(_home_shoot_ids() | set(scan_range))
    recent = []

    print(f"Candidate pool loaded: {len(candidates)}")
    print(
        f"Discovering scored ShootScoreBoard shoots across {len(ids)} IDs "
        f"(earliest MyATA cutoff {earliest})..."
    )

    for index, shoot_id in enumerate(ids, 1):
        if index == 1 or index % 25 == 0 or index == len(ids):
            print(
                f"  Discovery {index}/{len(ids)} "
                f"(shootid {shoot_id}) | scored recent found {len(recent)}",
                flush=True,
            )
        try:
            menu_html = fetch_text(
                f"{BASE_URL}menu.cfm?shootid={shoot_id}",
                timeout=4,
            )
            _name, start, end = parse_shoot_header(menu_html, shoot_id)
            if not (end > earliest and start <= today):
                continue

            entries_html = fetch_text(
                f"{BASE_URL}entrys.cfm?shootid={shoot_id}",
                timeout=4,
            )
            if not _event_specs_from_entries(entries_html):
                continue
        except KeyboardInterrupt:
            raise
        except Exception:
            continue

        recent.append(shoot_id)

    print(f"Recent scored shoots discovered: {len(recent)}", flush=True)
    return recent



def _candidate_identity_v461(candidate: Candidate) -> dict:
    """
    Derive identity primarily from display_name, which is the most reliable
    representation in the MNTrapTeam shooter table.  This avoids bad matches
    when first_name itself contains a middle initial/name.
    """
    tokens = _compact_name(candidate.display_name).split()

    suffix = ""
    if tokens and tokens[-1] in {"JR", "SR", "II", "III", "IV"}:
        suffix = tokens.pop()

    if len(tokens) >= 2:
        return {
            "first": tokens[0],
            "last": tokens[-1],
            "middle": tokens[1:-1],
            "suffix": suffix,
        }

    # Fallback only if display_name is unexpectedly sparse.
    first_tokens = _compact_name(candidate.first_name).split()
    last_tokens = _compact_name(candidate.last_name).split()

    first = first_tokens[0] if first_tokens else ""
    last = last_tokens[-1] if last_tokens else ""
    middle = first_tokens[1:] if len(first_tokens) > 1 else []

    return {
        "first": first,
        "last": last,
        "middle": middle,
        "suffix": suffix,
    }


def _row_orientations_v461(row_name: str) -> list[dict]:
    tokens = _compact_name(row_name).split()

    suffix = ""
    if tokens and tokens[-1] in {"JR", "SR", "II", "III", "IV"}:
        suffix = tokens.pop()

    if len(tokens) < 2:
        return []

    return [
        {
            "first": tokens[0],
            "last": tokens[-1],
            "middle": tokens[1:-1],
            "suffix": suffix,
        },
        {
            "first": tokens[1],
            "last": tokens[0],
            "middle": tokens[2:],
            "suffix": suffix,
        },
    ]


def _middle_compatible_v461(candidate_middle: list[str], row_middle: list[str]) -> bool:
    if not candidate_middle or not row_middle:
        return True

    c = candidate_middle[0]
    r = row_middle[0]

    if c == r:
        return True
    if len(c) == 1 and r.startswith(c):
        return True
    if len(r) == 1 and c.startswith(r):
        return True
    return False


def _last_name_compatible_v461(candidate_last: str, row_last: str) -> bool:
    if candidate_last == row_last:
        return True

    # Allow exactly one clipped trailing character, e.g. LARSO -> LARSON.
    return (
        len(candidate_last) >= 5
        and len(row_last) == len(candidate_last) - 1
        and candidate_last.startswith(row_last)
    )


def _match(candidates: list[Candidate], row_name: str, state: str) -> list[Candidate]:
    if str(state or "").upper() != "MN":
        return []

    orientations = _row_orientations_v461(row_name)
    if not orientations:
        return []

    matches = []

    for candidate in candidates:
        ident = _candidate_identity_v461(candidate)
        if not ident["first"] or not ident["last"]:
            continue

        for row in orientations:
            if ident["suffix"] != row["suffix"]:
                continue
            if ident["first"] != row["first"]:
                continue
            if not _last_name_compatible_v461(ident["last"], row["last"]):
                continue
            if not _middle_compatible_v461(ident["middle"], row["middle"]):
                continue

            matches.append(candidate)
            break

    return matches


def _event_date(shoot, event) -> str:
    """
    Resolve the actual event date for the common two-day ATA format:
    S/H/D on day 1 followed by S/H/D on day 2.

    If the event layout is not confidently recognized, retain the shoot
    start date rather than inventing a date.
    """
    start = str(getattr(shoot, "start_date", "") or "")
    end = str(getattr(shoot, "end_date", "") or "")
    events = list(getattr(shoot, "events", []) or [])

    if not end or start == end:
        return start

    ordered = sorted(events, key=lambda e: int(getattr(e, "event_id", 0)))
    disciplines = [str(getattr(e, "discipline", "") or "").lower() for e in ordered]

    if (
        len(ordered) == 6
        and disciplines == [
            "singles", "handicap", "doubles",
            "singles", "handicap", "doubles",
        ]
    ):
        first_ids = {int(e.event_id) for e in ordered[:3]}
        return start if int(event.event_id) in first_ids else end

    return start


def _stored_event_name(event) -> str:
    """
    Persist an event-specific name so repeated disciplines on multi-day shoots
    do not collide with the scores unique constraint.
    Example: E1 SINGLES, E4 SINGLES.
    """
    base = str(getattr(event, "name", "") or "").strip() or str(getattr(event, "discipline", "")).upper()
    return f"E{int(event.event_id)} {base}".strip()


def _duplicate(db, shooter_id, shoot_name, event_name, discipline, targets, hits):
    return bool(
        db.query(
            """
            SELECT sc.id
            FROM scores sc
            LEFT JOIN shoots sh ON sh.id=sc.shoot_id
            WHERE sc.shooter_id=?
              AND upper(COALESCE(sh.name,''))=upper(?)
              AND upper(COALESCE(sc.event_name,''))=upper(?)
              AND lower(COALESCE(sc.discipline,''))=lower(?)
              AND sc.targets=? AND sc.hits=?
            LIMIT 1
            """,
            (shooter_id, shoot_name, event_name, discipline, targets, hits),
        )
    )


def discover(db: Database, season: int, scan_range: range, debug_name: str = '', shoot_ids: list[int] | None = None) -> dict:
    candidates = _candidate_pool(db, season)
    if not candidates:
        raise RuntimeError("No baseline-ready locked Men's candidates found")

    if shoot_ids:
        shoot_ids = sorted(set(int(x) for x in shoot_ids))
        print(
            "Single/selected-shoot mode: skipping discovery; "
            f"using shoot IDs {', '.join(str(x) for x in shoot_ids)}",
            flush=True,
        )
    else:
        shoot_ids = _recent_ids(candidates, scan_range)
    found, overlaps, ambiguous, errors, debug_rows = [], [], [], [], []

    for index, shoot_id in enumerate(shoot_ids, 1):
        print(
            f"Scanning recent shoot {index}/{len(shoot_ids)} "
            f"(shootid {shoot_id})...",
            flush=True,
        )
        try:
            shoot = _load_shoot_from_entries(shoot_id, timeout=5)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(
                f"  SKIP shootid {shoot_id}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            errors.append(f"{shoot_id}: {exc}")
            continue

        for event in shoot.events:
            for row in event.entries:
                if debug_name and debug_name.upper() in str(row["name"]).upper():
                    debug_rows.append(
                        {
                            "shoot_id": shoot.shoot_id,
                            "shoot": shoot.name,
                            "start_date": _event_date(shoot, event),
                            "event_id": event.event_id,
                            "event_name": event.name,
                            "discipline": event.discipline,
                            "row_name": row["name"],
                            "state": row["state"],
                            "hits": row["hits"],
                            "targets": row["targets"],
                            "identity_key": _identity_key(row["name"]),
                            "matches": [
                                c.display_name
                                for c in _match(candidates, row["name"], row["state"])
                            ],
                        }
                    )

                matches = _match(candidates, row["name"], row["state"])
                if not matches:
                    continue
                if len(matches) != 1:
                    ambiguous.append((shoot, row, matches))
                    continue

                candidate = matches[0]
                event_date = _event_date(shoot, event)

                # Compare the actual event date to this shooter's MyATA cutoff.
                # If the event is on/before the official-through date, it is
                # already represented by the official baseline and must not be
                # layered in again.
                if event_date <= candidate.cutoff:
                    if shoot.start_date <= candidate.cutoff < shoot.end_date:
                        overlaps.append((candidate, shoot))
                    continue

                stored_event_name = _stored_event_name(event)
                if _duplicate(
                    db, candidate.shooter_id, shoot.name, stored_event_name,
                    event.discipline, int(row["targets"]), int(row["hits"])
                ):
                    continue

                found.append((candidate, shoot, event, row))

    return {
        "candidates": candidates,
        "shoot_ids": shoot_ids,
        "found": found,
        "overlaps": overlaps,
        "ambiguous": ambiguous,
        "errors": errors,
        "debug_rows": debug_rows,
    }


def _ensure_shoot(db: Database, shoot) -> int:
    rows = db.query(
        """
        SELECT id FROM shoots
        WHERE source_url=? OR (name=? AND start_date=?)
        ORDER BY id LIMIT 1
        """,
        (shoot.source_url, shoot.name, shoot.start_date),
    )
    if rows:
        return int(rows[0]["id"])
    return int(
        db.execute(
            """
            INSERT INTO shoots(name,club,city,state,start_date,end_date,source_type,source_url)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                shoot.name, shoot.name, "", "", shoot.start_date, shoot.end_date,
                "ShootScoreBoard recent-scout", shoot.source_url,
            ),
        )
    )


def write_found(db: Database, result: dict) -> int:
    written = 0
    for candidate, shoot, event, row in result["found"]:
        shoot_id = _ensure_shoot(db, shoot)
        db.execute(
            """
            INSERT INTO scores(
                shooter_id,shoot_id,event_date,event_name,discipline,
                targets,hits,in_state,club_key,source,official,raw_name
            ) VALUES(?,?,?,?,?,?,?,?,?,?,0,?)
            """,
            (
                candidate.shooter_id, shoot_id, _event_date(shoot, event), _stored_event_name(event),
                event.discipline, int(row["targets"]), int(row["hits"]),
                0, shoot.name, "ShootScoreBoard recent-scout", row["name"],
            ),
        )
        written += 1
    return written


def _print(result: dict) -> None:
    print("MNTrapTeam Recent Score Scout — Men's HAA Pool")
    print("==============================================")
    print(f"Baseline-ready Men's candidates: {len(result['candidates'])}")
    print(f"Recent scored ShootScoreBoard shoots inspected: {len(result['shoot_ids'])}")
    print(f"New candidate score rows found: {len(result['found'])}")
    print(f"Cutoff-overlap rows held: {len(result['overlaps'])}")
    print(f"Ambiguous rows held: {len(result['ambiguous'])}")
    print(f"Scored shoots skipped during report parse: {len(result['errors'])}")
    print()

    grouped = defaultdict(list)
    for candidate, shoot, event, row in result["found"]:
        grouped[candidate.display_name].append((candidate, shoot, event, row))

    for name in sorted(grouped):
        items = grouped[name]
        print(f"{name} | MyATA through {items[0][0].cutoff}")
        for _candidate, shoot, event, row in items:
            print(
                f"  + {_event_date(shoot, event)} | {shoot.name} | "
                f"{event.discipline} {row['hits']}/{row['targets']}"
            )

    if result["overlaps"]:
        print()
        print("OVERLAPPING SHOOTS — REVIEW, NOT AUTO-IMPORTED")
        seen = set()
        for candidate, shoot in result["overlaps"]:
            key = (candidate.shooter_id, shoot.shoot_id)
            if key in seen:
                continue
            seen.add(key)
            print(
                f"{candidate.display_name} | cutoff {candidate.cutoff} | "
                f"{shoot.start_date}–{shoot.end_date} | {shoot.name}"
            )

    if result["ambiguous"]:
        print()
        print("AMBIGUOUS NAMES — NOT IMPORTED")
        for shoot, row, matches in result["ambiguous"]:
            print(
                f"{shoot.name} | {row['name']} -> "
                + ", ".join(c.display_name for c in matches)
            )

    if result.get("debug_rows"):
        print()
        print("RAW NAME DEBUG")
        print("--------------")
        for item in result["debug_rows"]:
            matched = ", ".join(item["matches"]) if item["matches"] else "NO MATCH"
            print(
                f"shootid {item['shoot_id']} | {item['start_date']} | "
                f"E{item['event_id']} {item['discipline']} | "
                f"{item['row_name']} | state={item['state']} | "
                f"{item['hits']}/{item['targets']} | match={matched}"
            )
            print(f"  identity_key={item['identity_key']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preview", "write"), nargs="?", default="preview")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument(
        "--id-scan",
        type=_parse_scan_range,
        default=range(2000, 2201),
        help="Fallback ShootScoreBoard ID range, e.g. 1900:2300",
    )
    parser.add_argument(
        "--debug-name",
        default="",
        help="Print raw score rows containing this name fragment, e.g. LARSON",
    )
    parser.add_argument(
        "--shoot-id",
        type=int,
        action="append",
        default=[],
        help=(
            "Scan only this ShootScoreBoard shoot ID and skip discovery. "
            "May be repeated for multiple known shoots."
        ),
    )
    args = parser.parse_args()

    print("MNTrapTeam Recent Score Scout starting...", flush=True)
    print(
        "Public ShootScoreBoard scan using Event Entries; no browser login is required.",
        flush=True,
    )
    db = Database(DATA / "mntrapteam.db")
    result = discover(db, args.season, args.id_scan, args.debug_name, args.shoot_id)
    _print(result)

    if args.action == "preview":
        print()
        print("PREVIEW ONLY — no database changes made.")
        return 0

    written = write_found(db, result)
    print()
    print(f"Provisional score rows written: {written}")
    print("Official MyATA season_stats were NOT rebuilt or modified.")
    print(
        "These rows affect Current HOA/total targets only until shoot location "
        "is classified for Minnesota in-state credit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
