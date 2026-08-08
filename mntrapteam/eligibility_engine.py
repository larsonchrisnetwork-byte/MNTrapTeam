from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MEN_OPEN_REQUIREMENTS = {
    "total_singles": 1500,
    "total_handicap": 1200,
    "total_doubles": 100,
    "mn_singles": 700,
    "mn_handicap": 700,
    "mn_doubles": 700,
    "mn_clubs": 4,
}


@dataclass(frozen=True)
class EligibilityResult:
    shooter_id: int
    season: int
    haa_gate: bool
    haa_source: str
    total_targets_ok: bool
    mn_targets_ok: bool
    clubs_ok: bool
    eligible: bool
    reasons: tuple[str, ...]
    values: dict[str, Any]


def _row_dict(row):
    return dict(row) if row is not None else None


def evaluate_mens_open(db, shooter_id: int, season: int = 2026) -> EligibilityResult:
    req = MEN_OPEN_REQUIREMENTS

    stats_rows = db.query(
        """
        SELECT *
        FROM season_stats
        WHERE shooter_id=? AND season=?
        ORDER BY
          CASE WHEN lower(COALESCE(source,'')) LIKE 'myata%' THEN 0 ELSE 1 END,
          rowid DESC
        LIMIT 1
        """,
        (shooter_id, season),
    )
    stats = _row_dict(stats_rows[0]) if stats_rows else {}

    state_haa_rows = db.query(
        """
        SELECT COUNT(*) AS n
        FROM haa_qualifications
        WHERE shooter_id=? AND season=? AND verified=1
        """,
        (shooter_id, season),
    )
    state_haa = bool(state_haa_rows and int(dict(state_haa_rows[0])["n"] or 0) > 0)

    zone_haa = False
    try:
        zone_rows = db.query(
            """
            SELECT COUNT(*) AS n
            FROM zone_haa_qualifications
            WHERE shooter_id=? AND season=? AND verified=1
            """,
            (shooter_id, season),
        )
        zone_haa = bool(zone_rows and int(dict(zone_rows[0])["n"] or 0) > 0)
    except Exception:
        zone_haa = False

    haa_gate = state_haa or zone_haa
    if state_haa and zone_haa:
        haa_source = "State HAA + verified home-zone HAA"
    elif state_haa:
        haa_source = "State HAA"
    elif zone_haa:
        haa_source = "Verified home-zone HAA"
    else:
        haa_source = "None"

    def ivalue(*names):
        for name in names:
            if name in stats and stats.get(name) is not None:
                try:
                    return int(stats.get(name) or 0)
                except Exception:
                    pass
        return 0

    total_s = ivalue("singles_targets", "total_singles_targets")
    total_h = ivalue("handicap_targets", "total_handicap_targets")
    total_d = ivalue("doubles_targets", "total_doubles_targets")

    mn_s = ivalue("mn_singles_targets", "in_state_singles_targets")
    mn_h = ivalue("mn_handicap_targets", "in_state_handicap_targets")
    mn_d = ivalue("mn_doubles_targets", "in_state_doubles_targets")
    clubs = ivalue("mn_clubs", "in_state_clubs", "club_count")

    total_targets_ok = (
        total_s >= req["total_singles"]
        and total_h >= req["total_handicap"]
        and total_d >= req["total_doubles"]
    )
    mn_targets_ok = (
        mn_s >= req["mn_singles"]
        and mn_h >= req["mn_handicap"]
        and mn_d >= req["mn_doubles"]
    )
    clubs_ok = clubs >= req["mn_clubs"]

    reasons = []
    if not haa_gate:
        reasons.append("HAA gate not met: need State HAA or verified HAA at home Zone shoot")
    if total_s < req["total_singles"]:
        reasons.append(f"Total Singles {total_s}/{req['total_singles']}")
    if total_h < req["total_handicap"]:
        reasons.append(f"Total Handicap {total_h}/{req['total_handicap']}")
    if total_d < req["total_doubles"]:
        reasons.append(f"Total Doubles {total_d}/{req['total_doubles']}")
    if mn_s < req["mn_singles"]:
        reasons.append(f"MN Singles {mn_s}/{req['mn_singles']}")
    if mn_h < req["mn_handicap"]:
        reasons.append(f"MN Handicap {mn_h}/{req['mn_handicap']}")
    if mn_d < req["mn_doubles"]:
        reasons.append(f"MN Doubles {mn_d}/{req['mn_doubles']}")
    if clubs < req["mn_clubs"]:
        reasons.append(f"MN Clubs {clubs}/{req['mn_clubs']}")

    eligible = haa_gate and total_targets_ok and mn_targets_ok and clubs_ok

    return EligibilityResult(
        shooter_id=shooter_id,
        season=season,
        haa_gate=haa_gate,
        haa_source=haa_source,
        total_targets_ok=total_targets_ok,
        mn_targets_ok=mn_targets_ok,
        clubs_ok=clubs_ok,
        eligible=eligible,
        reasons=tuple(reasons),
        values={
            "total_singles": total_s,
            "total_handicap": total_h,
            "total_doubles": total_d,
            "mn_singles": mn_s,
            "mn_handicap": mn_h,
            "mn_doubles": mn_d,
            "mn_clubs": clubs,
        },
    )
