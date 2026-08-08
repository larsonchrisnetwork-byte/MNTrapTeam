$ErrorActionPreference = "Stop"

$ProjectRoot = "H:\MNTrapTeam\MNTrapTeam"
$TargetFile = Join-Path $ProjectRoot "mntrapteam\recent_score_scout_cli.py"
$VersionFile = Join-Path $ProjectRoot "VERSION"
$InitFile = Join-Path $ProjectRoot "mntrapteam\__init__.py"
$GuiFile = Join-Path $ProjectRoot "mntrapteam\gui.py"
$Version = "4.4.1"

if (-not (Test-Path (Join-Path $ProjectRoot "mntrapteam"))) {
    throw "MNTrapTeam project not found at $ProjectRoot"
}

Write-Host "Installing MNTrapTeam $Version Recent Score Scout..."
Write-Host ""

$PythonSource = @'
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
from .shootscoreboard_web import BASE_URL, fetch_text, load_public_shoot, parse_shoot_header
from .state_team_lock import ensure_schema as ensure_lock_schema


@dataclass(frozen=True)
class Candidate:
    shooter_id: int
    ata_number: str
    display_name: str
    first_name: str
    last_name: str
    cutoff: str


def _compact_name(value: str) -> str:
    text = re.sub(r"[^A-Z0-9 ]+", " ", str(value or "").upper())
    return " ".join(t for t in text.split() if t)


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
        f"Discovering ShootScoreBoard shoots across {len(ids)} IDs "
        f"(earliest MyATA cutoff {earliest})..."
    )

    for index, shoot_id in enumerate(ids, 1):
        if index == 1 or index % 25 == 0 or index == len(ids):
            print(
                f"  Discovery {index}/{len(ids)} "
                f"(shootid {shoot_id}) | recent found {len(recent)}",
                flush=True,
            )
        try:
            html = fetch_text(
                f"{BASE_URL}menu.cfm?shootid={shoot_id}",
                timeout=4,
            )
            _name, start, end = parse_shoot_header(html, shoot_id)
        except KeyboardInterrupt:
            raise
        except Exception:
            continue

        if end > earliest and start <= today:
            recent.append(shoot_id)

    print(f"Recent candidate shoots discovered: {len(recent)}", flush=True)
    return recent


def _match(candidates: list[Candidate], row_name: str, state: str) -> list[Candidate]:
    if str(state or "").upper() != "MN":
        return []
    key = _compact_name(row_name)
    return [
        c for c in candidates
        if key in _name_keys(c.display_name, c.first_name, c.last_name)
    ]


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


def discover(db: Database, season: int, scan_range: range) -> dict:
    candidates = _candidate_pool(db, season)
    if not candidates:
        raise RuntimeError("No baseline-ready locked Men's candidates found")

    shoot_ids = _recent_ids(candidates, scan_range)
    found, overlaps, ambiguous, errors = [], [], [], []

    def scout_fetcher(url: str) -> str:
        return fetch_text(url, timeout=5)

    for index, shoot_id in enumerate(shoot_ids, 1):
        print(
            f"Scanning recent shoot {index}/{len(shoot_ids)} "
            f"(shootid {shoot_id})...",
            flush=True,
        )
        try:
            shoot = load_public_shoot(shoot_id, fetcher=scout_fetcher)
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
                matches = _match(candidates, row["name"], row["state"])
                if not matches:
                    continue
                if len(matches) != 1:
                    ambiguous.append((shoot, row, matches))
                    continue

                candidate = matches[0]
                if shoot.start_date <= candidate.cutoff < shoot.end_date:
                    overlaps.append((candidate, shoot))
                    continue
                if shoot.start_date <= candidate.cutoff:
                    continue
                if _duplicate(
                    db, candidate.shooter_id, shoot.name, event.name,
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
                candidate.shooter_id, shoot_id, shoot.start_date, event.name,
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
    print(f"Recent ShootScoreBoard shoots inspected: {len(result['shoot_ids'])}")
    print(f"New candidate score rows found: {len(result['found'])}")
    print(f"Cutoff-overlap rows held: {len(result['overlaps'])}")
    print(f"Ambiguous rows held: {len(result['ambiguous'])}")
    print(f"Shoot pages skipped: {len(result['errors'])}")
    print()

    grouped = defaultdict(list)
    for candidate, shoot, event, row in result["found"]:
        grouped[candidate.display_name].append((candidate, shoot, event, row))

    for name in sorted(grouped):
        items = grouped[name]
        print(f"{name} | MyATA through {items[0][0].cutoff}")
        for _candidate, shoot, event, row in items:
            print(
                f"  + {shoot.start_date} | {shoot.name} | "
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
    args = parser.parse_args()

    print("MNTrapTeam Recent Score Scout starting...", flush=True)
    print(
        "Public ShootScoreBoard scan; no browser login is required.",
        flush=True,
    )
    db = Database(DATA / "mntrapteam.db")
    result = discover(db, args.season, args.id_scan)
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

'@

Set-Content -Path $TargetFile -Value $PythonSource -Encoding UTF8
Write-Host "Updated: mntrapteam\recent_score_scout_cli.py"

Set-Content -Path $VersionFile -Value $Version -Encoding UTF8
Write-Host "Updated: VERSION -> $Version"

if (Test-Path $InitFile) {
    $InitText = Get-Content $InitFile -Raw
    if ($InitText -match '__version__\s*=') {
        $InitText = [regex]::Replace(
            $InitText,
            '__version__\s*=\s*["''][^"'']+["'']',
            '__version__ = "4.4.1"',
            1
        )
    } else {
        $InitText = $InitText.TrimEnd() + "`r`n__version__ = `"4.4.1`"`r`n"
    }
    Set-Content -Path $InitFile -Value $InitText -Encoding UTF8
    Write-Host "Updated: mntrapteam\__init__.py"
}

if (Test-Path $GuiFile) {
    $GuiText = Get-Content $GuiFile -Raw
    $GuiText = [regex]::Replace(
        $GuiText,
        'MNTrapTeam \d+\.\d+\.\d+',
        'MNTrapTeam 4.4.1',
        1
    )
    Set-Content -Path $GuiFile -Value $GuiText -Encoding UTF8
    Write-Host "Updated: mntrapteam\gui.py version"
}

Set-Location $ProjectRoot

Write-Host ""
Write-Host "Checking Python syntax..."
& ".\.venv\Scripts\python.exe" -m py_compile ".\mntrapteam\recent_score_scout_cli.py"
if ($LASTEXITCODE -ne 0) {
    throw "Python syntax check failed."
}

Write-Host "Syntax check passed."
Write-Host ""
Write-Host "MNTrapTeam $Version scout update installed."
Write-Host ""
Write-Host "Next run:"
Write-Host '& ".\.venv\Scripts\python.exe" -m mntrapteam.recent_score_scout_cli preview --id-scan 2050:2125'
