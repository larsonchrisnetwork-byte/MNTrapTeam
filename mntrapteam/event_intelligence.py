from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .calculations import DISCIPLINES, average
from .season import season_bounds


@dataclass(frozen=True)
class PersonalBest:
    discipline: str
    hits: int
    targets: int
    average: float
    event_date: str
    event_name: str
    club: str


def _season_strings(season: int) -> tuple[str, str]:
    start, end = season_bounds(int(season))
    return str(start), str(end)


def shooter_events(database, shooter_id: int, season: int) -> list[dict[str, Any]]:
    start, end = _season_strings(season)
    rows = database.query(
        '''
        SELECT
            sc.id, sc.event_date, sc.event_name, sc.discipline,
            sc.targets, sc.hits, sc.in_state, sc.club_key,
            sc.source, sc.official,
            sh.name AS shoot_name, sh.club, sh.city, sh.state
        FROM scores sc
        LEFT JOIN shoots sh ON sh.id=sc.shoot_id
        WHERE sc.shooter_id=?
          AND sc.event_date BETWEEN ? AND ?
        ORDER BY sc.event_date ASC, sc.id ASC
        ''',
        (shooter_id, start, end),
    )
    for row in rows:
        row["average"] = average(row["hits"], row["targets"])
        row["club_display"] = (
            row.get("club")
            or row.get("club_key")
            or row.get("shoot_name")
            or ""
        )
        row["month"] = str(row.get("event_date") or "")[:7]
        row["straight"] = bool(
            int(row.get("targets") or 0) > 0
            and int(row.get("hits") or 0) == int(row.get("targets") or 0)
        )
    return rows


def aggregate_by(events: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        group_value = str(event.get(key) or "Unknown")
        discipline = str(event.get("discipline") or "")
        group_key = (group_value, discipline)
        item = grouped.setdefault(
            group_key,
            {
                key: group_value,
                "discipline": discipline,
                "targets": 0,
                "hits": 0,
                "events": 0,
                "straights": 0,
            },
        )
        item["targets"] += int(event.get("targets") or 0)
        item["hits"] += int(event.get("hits") or 0)
        item["events"] += 1
        item["straights"] += int(bool(event.get("straight")))

    rows = []
    for item in grouped.values():
        item["average"] = average(item["hits"], item["targets"])
        rows.append(item)

    return sorted(
        rows,
        key=lambda row: (
            str(row[key]).lower(),
            DISCIPLINES.index(row["discipline"])
            if row["discipline"] in DISCIPLINES
            else 99,
        ),
    )


def club_performance(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return aggregate_by(events, "club_display")


def monthly_performance(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return aggregate_by(events, "month")


def personal_bests(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for event in events:
        discipline = event.get("discipline")
        if discipline not in DISCIPLINES:
            continue
        candidate = {
            "discipline": discipline,
            "hits": int(event.get("hits") or 0),
            "targets": int(event.get("targets") or 0),
            "average": float(event.get("average") or 0),
            "event_date": str(event.get("event_date") or ""),
            "event_name": str(event.get("event_name") or ""),
            "club": str(event.get("club_display") or ""),
        }
        current = best.get(discipline)
        if current is None:
            best[discipline] = candidate
            continue
        candidate_key = (
            candidate["average"],
            candidate["targets"],
            candidate["hits"],
            candidate["event_date"],
        )
        current_key = (
            current["average"],
            current["targets"],
            current["hits"],
            current["event_date"],
        )
        if candidate_key > current_key:
            best[discipline] = candidate
    return [best[d] for d in DISCIPLINES if d in best]


def recent_form(events: list[dict[str, Any]], target_window: int = 500) -> list[dict[str, Any]]:
    if target_window <= 0:
        raise ValueError("target_window must be positive")
    newest_first = list(reversed(events))
    output = []
    for discipline in DISCIPLINES:
        targets = 0
        hits = 0
        used_events = 0
        for event in newest_first:
            if event.get("discipline") != discipline:
                continue
            targets += int(event.get("targets") or 0)
            hits += int(event.get("hits") or 0)
            used_events += 1
            if targets >= target_window:
                break
        output.append(
            {
                "discipline": discipline,
                "targets": targets,
                "hits": hits,
                "average": average(hits, targets),
                "events": used_events,
                "requested_window": target_window,
            }
        )
    return output


def season_event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        discipline: {"targets": 0, "hits": 0, "events": 0, "straights": 0}
        for discipline in DISCIPLINES
    }
    clubs = set()
    mn_clubs = set()

    for event in events:
        discipline = event.get("discipline")
        if discipline not in totals:
            continue
        totals[discipline]["targets"] += int(event.get("targets") or 0)
        totals[discipline]["hits"] += int(event.get("hits") or 0)
        totals[discipline]["events"] += 1
        totals[discipline]["straights"] += int(bool(event.get("straight")))
        club = str(event.get("club_display") or "").strip()
        if club:
            clubs.add(club)
            if event.get("in_state"):
                mn_clubs.add(club)

    rows = []
    for discipline in DISCIPLINES:
        item = {"discipline": discipline, **totals[discipline]}
        item["average"] = average(item["hits"], item["targets"])
        rows.append(item)

    return {
        "disciplines": rows,
        "event_rows": len(events),
        "clubs": len(clubs),
        "mn_clubs": len(mn_clubs),
        "total_targets": sum(item["targets"] for item in rows),
        "total_hits": sum(item["hits"] for item in rows),
        "total_straights": sum(item["straights"] for item in rows),
    }


def event_intelligence(database, shooter_id: int, season: int, recent_window: int = 500) -> dict[str, Any]:
    events = shooter_events(database, shooter_id, season)
    return {
        "events": list(reversed(events)),
        "summary": season_event_summary(events),
        "recent_form": recent_form(events, recent_window),
        "personal_bests": personal_bests(events),
        "clubs": club_performance(events),
        "months": monthly_performance(events),
    }
