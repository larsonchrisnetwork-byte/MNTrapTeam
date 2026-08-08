from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import re

from rapidfuzz import fuzz, process

from .paths import DATA


def normalize_club_name(value: str) -> str:
    text = str(value or "").upper()
    text = text.replace("&", " AND ")
    text = re.sub(r"\bASSN\b", "ASSOCIATION", text)
    text = re.sub(r"\bASSOC\b", "ASSOCIATION", text)
    text = re.sub(r"\bGUN CLUB\b", "GUN CLUB", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


MN_CLUB_ALIASES = {
    "ALEXANDRIA SHOOTING PARK": {"club_id": "MN-MTA-ALEXANDRIA", "name": "Alexandria Shooting Park", "state": "MN"},
    "BALD EAGLE SPORTSMENS ASSN": {"club_id": "MN-MTA-BALDEAGLE", "name": "Bald Eagle Sportsmen's Assn", "state": "MN"},
    "BEAVERBROOK TRI CO CLUB": {"club_id": "MN-MTA-BEAVERBROOK", "name": "Beaverbrook Tri-Co Club", "state": "MN"},
    "BEAVER BROOK TRI COUNTY GUN CLUB": {"club_id": "MN-MTA-BEAVERBROOK", "name": "Beaverbrook Tri-Co Club", "state": "MN"},
    "BECKER CO SPORTSMENS CLUB": {"club_id": "MN-MTA-BECKER", "name": "Becker Co Sportsmens Club", "state": "MN"},
    "BEMIDJI TRAP AND SKEET CLUB": {"club_id": "MN-MTA-BEMIDJI", "name": "Bemidji Trap & Skeet Club", "state": "MN"},
    "BUFFALO GUN CLUB": {"club_id": "MN-MTA-BUFFALO", "name": "Buffalo Gun Club", "state": "MN"},
    "DEL TONE GUN RANGE": {"club_id": "MN-MTA-DELTONE", "name": "Del-Tone Gun Range", "state": "MN"},
    "DEL TONE SHOOTING RANGE": {"club_id": "MN-MTA-DELTONE", "name": "Del-Tone Gun Range", "state": "MN"},
    "FAIRMONT TRAP CLUB": {"club_id": "MN-MTA-FAIRMONT", "name": "Fairmont Trap Club Inc", "state": "MN"},
    "FAIRMONT TRAP CLUB INC": {"club_id": "MN-MTA-FAIRMONT", "name": "Fairmont Trap Club Inc", "state": "MN"},
    "FOREST LAKE SPORTSMENS CLUB": {"club_id": "MN-MTA-FORESTLAKE", "name": "Forest Lake Sportsmens Club", "state": "MN"},
    "GLENWOOD GUN CLUB": {"club_id": "MN-MTA-GLENWOOD", "name": "Glenwood Gun Club", "state": "MN"},
    "GRAND RAPIDS GUN CLUB": {"club_id": "MN-MTA-GRANDRAPIDS", "name": "Grand Rapids Gun Club", "state": "MN"},
    "MN CLAY TARGET SPORTS GRAND RAPIDS": {"club_id": "MN-MTA-GRANDRAPIDS", "name": "Grand Rapids Gun Club", "state": "MN"},
    "HIBBING TRAP CLUB": {"club_id": "MN-MTA-HIBBING", "name": "Hibbing Trap Club", "state": "MN"},
    "HUNTERSVILLE SPORTSMENS PARK": {"club_id": "MN-MTA-HUNTERSVILLE", "name": "Huntersville Sportsmen's Park", "state": "MN"},
    "LAKESHORE CONSERVATION CLUB": {"club_id": "MN-MTA-LAKESHORE", "name": "Lakeshore Conservation Club", "state": "MN"},
    "LESTER PRAIRIE SPORTSMENS CLUB": {"club_id": "MN-MTA-LESTERPRAIRIE", "name": "Lester Prairie Sportsmens Club", "state": "MN"},
    "MINNEAPOLIS GUN CLUB": {"club_id": "MN-MTA-MINNEAPOLIS", "name": "Minneapolis Gun Club", "state": "MN"},
    "MINNESOTA SPORTSMENS CLUB ZIMMERMAN": {"club_id": "MN-MTA-ZIMMERMAN", "name": "Minnesota Sportsmens Club (Zimmerman)", "state": "MN"},
    "MINNESOTA YOUTH SHOTGUN ASSN": {"club_id": "MN-MTA-MYSA", "name": "Minnesota Youth Shotgun Assn", "state": "MN"},
    "MINNESOTA TRAP ASSOCIATION": {"club_id": "MN-MTA-MTA", "name": "Minnesota Trap Association", "state": "MN"},
    "MINNESOTA TRAP ASSN": {"club_id": "MN-MTA-MTA", "name": "Minnesota Trap Association", "state": "MN"},
    "MONTICELLO ROD AND GUN CLUB": {"club_id": "MN-MTA-MONTICELLORG", "name": "Monticello Rod & Gun Club", "state": "MN"},
    "MONTICELLO SPORTSMENS CLUB": {"club_id": "MN-MTA-MONTICELLO", "name": "Monticello Sportsmens Club", "state": "MN"},
    "MORRISTOWN GUN CLUB": {"club_id": "MN-MTA-MORRISTOWN", "name": "Morristown Gun Club", "state": "MN"},
    "OWATONNA GUN CLUB": {"club_id": "MN-MTA-OWATONNA", "name": "Owatonna Gun Club", "state": "MN"},
    "PROCTOR JACK MEAD GUN CLUB": {"club_id": "MN-MTA-PROCTOR", "name": "Proctor Jack Mead Gun Club", "state": "MN"},
    "SHOOTERS SPORTING CLAYS MARSHALL": {"club_id": "MN-MTA-MARSHALL", "name": "Shooters Sporting Clays (Marshall)", "state": "MN"},
    "WATERTOWN ROD AND GUN CLUB": {"club_id": "MN-MTA-WATERTOWN", "name": "Watertown Rod & Gun Club", "state": "MN"},
    "WINONA SPORTSMENS CLUB": {"club_id": "MN-MTA-WINONA", "name": "Winona Sportsmens Club", "state": "MN"},
}



@dataclass
class ClubMatch:
    raw_name: str
    canonical_name: str = ""
    state: str = ""
    club_id: str = ""
    score: float = 0.0
    method: str = ""
    confident: bool = False

    @property
    def is_minnesota(self) -> bool:
        return self.confident and self.state == "MN"


class SOSClubDirectory:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = []
        self.by_normalized: dict[str, list[dict[str, Any]]] = {}
        self.mn_aliases = {
            normalize_club_name(key): value
            for key, value in MN_CLUB_ALIASES.items()
        }

        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            item = {
                "club_id": str(row.get("clubId") or ""),
                "name": name,
                "state": str(row.get("stateProvince") or "").strip().upper(),
                "normalized": normalize_club_name(name),
            }
            self.rows.append(item)
            self.by_normalized.setdefault(item["normalized"], []).append(item)

        self.choices = [row["normalized"] for row in self.rows]

    @classmethod
    def from_latest_capture(cls, data_dir: Path = DATA) -> "SOSClubDirectory":
        root = Path(data_dir) / "connector_downloads" / "sos"
        candidates: list[tuple[float, Path, list[dict[str, Any]]]] = []

        if not root.exists():
            raise FileNotFoundError(
                "No SOS capture directory exists. Run the SOS discovery capture first."
            )

        for path in root.rglob("*.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            payload = raw.get("payload") if isinstance(raw, dict) else None
            if not isinstance(payload, list) or not payload:
                continue
            first = payload[0]
            if not isinstance(first, dict):
                continue

            keys = set(first)
            if {"clubId", "name", "stateProvince"}.issubset(keys):
                candidates.append((path.stat().st_mtime, path, payload))

        if not candidates:
            raise FileNotFoundError(
                "No SOS club-list JSON was found in connector captures."
            )

        _mtime, path, rows = sorted(candidates, key=lambda item: item[0])[-1]
        directory = cls(rows)
        directory.source_path = path
        return directory

    def match(self, raw_name: str) -> ClubMatch:
        raw = str(raw_name or "").strip()
        normalized = normalize_club_name(raw)

        if not normalized:
            return ClubMatch(raw_name=raw, method="blank")

        # Hard authoritative MTA overrides for MyATA spellings that have
        # repeatedly bypassed alias/fuzzy matching in production.
        hard_mn = {
            "BEMIDJI TRAP AND SKEET GUN CLUB": (
                "MN-MTA-BEMIDJI", "Bemidji Trap & Skeet Club"
            ),
            "BEMIDJI TRAP AND SKEET CLUB": (
                "MN-MTA-BEMIDJI", "Bemidji Trap & Skeet Club"
            ),
            "FAIRMONT TRAP CLUB INC": (
                "MN-MTA-FAIRMONT", "Fairmont Trap Club Inc"
            ),
            "FOREST LAKE SPORTSMENS CLUB": (
                "MN-MTA-FORESTLAKE", "Forest Lake Sportsmens Club"
            ),
        }

        override = hard_mn.get(normalized)
        if override:
            club_id, canonical_name = override
            return ClubMatch(
                raw_name=raw,
                canonical_name=canonical_name,
                state="MN",
                club_id=club_id,
                score=100.0,
                method="mta-hard-override",
                confident=True,
            )

        alias = self.mn_aliases.get(normalized)
        if alias:
            return ClubMatch(
                raw_name=raw,
                canonical_name=alias["name"],
                state=alias["state"],
                club_id=alias["club_id"],
                score=100.0,
                method="mn-alias",
                confident=True,
            )

        exact = self.by_normalized.get(normalized, [])
        if len(exact) == 1:
            row = exact[0]
            return ClubMatch(
                raw_name=raw,
                canonical_name=row["name"],
                state=row["state"],
                club_id=row["club_id"],
                score=100.0,
                method="exact",
                confident=True,
            )

        if len(exact) > 1:
            states = {row["state"] for row in exact}
            if len(states) == 1:
                row = exact[0]
                return ClubMatch(
                    raw_name=raw,
                    canonical_name=row["name"],
                    state=row["state"],
                    club_id=row["club_id"],
                    score=100.0,
                    method="exact-shared-state",
                    confident=True,
                )

        # Conservative fuzzy match. We intentionally refuse uncertain matches
        # rather than accidentally counting an out-of-state club as Minnesota.
        matches = process.extract(
            normalized,
            self.choices,
            scorer=fuzz.ratio,
            limit=5,
        )

        if not matches:
            return ClubMatch(raw_name=raw, method="unmatched")

        best_norm, best_score, best_index = matches[0]
        best = self.rows[best_index]

        runner_score = 0.0
        for candidate_norm, score, candidate_index in matches[1:]:
            candidate = self.rows[candidate_index]
            if candidate["state"] != best["state"] or candidate_norm != best_norm:
                runner_score = float(score)
                break

        confident = (
            float(best_score) >= 94.0
            and (
                runner_score == 0.0
                or float(best_score) - runner_score >= 3.0
            )
        )

        return ClubMatch(
            raw_name=raw,
            canonical_name=best["name"],
            state=best["state"],
            club_id=best["club_id"],
            score=float(best_score),
            method="fuzzy",
            confident=confident,
        )


@dataclass
class MNEnrichmentTotals:
    singles_targets: int = 0
    handicap_targets: int = 0
    doubles_targets: int = 0
    mn_clubs: int = 0
    unknown_clubs: tuple[str, ...] = ()
    matched_clubs: tuple[str, ...] = ()


def _integer(value: Any) -> int:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def enrich_score_detail_rows(
    rows: list[list[str]],
    directory: SOSClubDirectory,
) -> MNEnrichmentTotals:
    singles = 0
    handicap = 0
    doubles = 0
    clubs: set[str] = set()
    matched: set[str] = set()
    unknown: set[str] = set()

    for cells in rows:
        if len(cells) < 14:
            continue

        date = str(cells[1] if len(cells) > 1 else "").strip()
        club = str(cells[2] if len(cells) > 2 else "").strip()

        if not re.search(r"\d", date):
            continue

        s_targets = _integer(cells[3])
        h_targets = _integer(cells[9])
        d_targets = _integer(cells[12])

        if s_targets + h_targets + d_targets <= 0:
            continue

        match = directory.match(club)

        if not match.confident:
            if club:
                unknown.add(club)
            continue

        if match.state != "MN":
            continue

        singles += s_targets
        handicap += h_targets
        doubles += d_targets

        club_key = match.club_id or normalize_club_name(match.canonical_name)
        if club_key:
            clubs.add(club_key)
        matched.add(f"{club} -> {match.canonical_name}")

    return MNEnrichmentTotals(
        singles_targets=singles,
        handicap_targets=handicap,
        doubles_targets=doubles,
        mn_clubs=len(clubs),
        unknown_clubs=tuple(sorted(unknown)),
        matched_clubs=tuple(sorted(matched)),
    )


def ensure_status_table(database) -> None:
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS myata_mn_enrichment (
            shooter_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            mn_singles_targets INTEGER NOT NULL DEFAULT 0,
            mn_handicap_targets INTEGER NOT NULL DEFAULT 0,
            mn_doubles_targets INTEGER NOT NULL DEFAULT 0,
            mn_clubs INTEGER NOT NULL DEFAULT 0,
            unknown_clubs TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (shooter_id, season)
        )
        """
    )


def save_enrichment(
    database,
    shooter_id: int,
    season: int,
    totals: MNEnrichmentTotals,
) -> None:
    ensure_status_table(database)

    database.execute(
        """
        INSERT INTO myata_mn_enrichment(
            shooter_id, season,
            mn_singles_targets, mn_handicap_targets,
            mn_doubles_targets, mn_clubs,
            unknown_clubs, updated_at
        )
        VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(shooter_id,season) DO UPDATE SET
            mn_singles_targets=excluded.mn_singles_targets,
            mn_handicap_targets=excluded.mn_handicap_targets,
            mn_doubles_targets=excluded.mn_doubles_targets,
            mn_clubs=excluded.mn_clubs,
            unknown_clubs=excluded.unknown_clubs,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            shooter_id,
            season,
            totals.singles_targets,
            totals.handicap_targets,
            totals.doubles_targets,
            totals.mn_clubs,
            "\n".join(totals.unknown_clubs),
        ),
    )

    # Update only Minnesota eligibility fields. Official total targets/hits are
    # deliberately untouched.
    database.upsert_stats(
        shooter_id,
        season,
        mn_singles_targets=totals.singles_targets,
        mn_handicap_targets=totals.handicap_targets,
        mn_doubles_targets=totals.doubles_targets,
        mn_clubs=totals.mn_clubs,
    )
