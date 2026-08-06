from __future__ import annotations

from typing import Any

from .calculations import DISCIPLINES, average
from .season import season_bounds


def shooter_by_ata(database, ata_number: str) -> dict[str, Any] | None:
    ata = "".join(ch for ch in str(ata_number or "") if ch.isdigit())
    if not ata:
        return None
    rows = database.query(
        "SELECT * FROM shooters WHERE ata_number=? AND active=1",
        (ata,),
    )
    return rows[0] if rows else None


def event_history(database, shooter_id: int, season: int, limit: int | None = None):
    start, end = season_bounds(int(season))
    sql = '''
        SELECT
            sc.id, sc.event_date, sc.event_name, sc.discipline,
            sc.targets, sc.hits, sc.in_state, sc.club_key,
            sc.source, sc.official,
            sh.name AS shoot_name, sh.club, sh.city, sh.state
        FROM scores sc
        LEFT JOIN shoots sh ON sh.id=sc.shoot_id
        WHERE sc.shooter_id=?
          AND sc.event_date BETWEEN ? AND ?
        ORDER BY sc.event_date DESC, sc.id DESC
    '''
    params = [shooter_id, str(start), str(end)]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    rows = database.query(sql, tuple(params))
    for row in rows:
        row["average"] = average(row["hits"], row["targets"])
        row["location"] = ", ".join(
            str(value).strip()
            for value in (row.get("club"), row.get("city"), row.get("state"))
            if value
        )
        row["mn"] = bool(row.get("in_state"))
    return rows


def discipline_progress(database, shooter_id: int, season: int):
    start, end = season_bounds(int(season))
    rows = database.query(
        '''
        SELECT discipline,
               SUM(targets) AS targets,
               SUM(hits) AS hits,
               SUM(CASE WHEN in_state=1 THEN targets ELSE 0 END) AS mn_targets,
               COUNT(*) AS events,
               COUNT(DISTINCT CASE WHEN in_state=1 THEN club_key END) AS mn_clubs
        FROM scores
        WHERE shooter_id=?
          AND event_date BETWEEN ? AND ?
        GROUP BY discipline
        ''',
        (shooter_id, str(start), str(end)),
    )
    indexed = {row["discipline"]: row for row in rows}
    output = {}
    for discipline in DISCIPLINES:
        row = indexed.get(discipline, {})
        targets = int(row.get("targets") or 0)
        hits = int(row.get("hits") or 0)
        output[discipline] = {
            "discipline": discipline,
            "targets": targets,
            "hits": hits,
            "average": average(hits, targets),
            "mn_targets": int(row.get("mn_targets") or 0),
            "events": int(row.get("events") or 0),
            "mn_clubs": int(row.get("mn_clubs") or 0),
        }
    return output


def rolling_event_average(events, discipline: str, window_targets: int = 500):
    if window_targets <= 0:
        raise ValueError("window_targets must be positive")

    targets = 0
    hits = 0
    for event in events:
        if event.get("discipline") != discipline:
            continue
        targets += int(event.get("targets") or 0)
        hits += int(event.get("hits") or 0)
        if targets >= window_targets:
            break
    return average(hits, targets)


def personal_progress(database, team_service, season: int, ata_number: str):
    shooter = shooter_by_ata(database, ata_number)
    if shooter is None:
        return {
            "found": False,
            "message": "No active shooter matches the ATA number saved in Settings.",
        }

    season_rows = team_service.season_rows(season)
    season_row = next(
        (row for row in season_rows if int(row["id"]) == int(shooter["id"])),
        None,
    )
    if season_row is None:
        return {
            "found": True,
            "has_stats": False,
            "shooter": shooter,
            "message": "The shooter exists, but no season statistics are available.",
            "events": event_history(database, shooter["id"], season, 50),
            "disciplines": discipline_progress(database, shooter["id"], season),
        }

    category = season_row.get("category_declared") or season_row.get("category")
    team = team_service.rules.team_for_category(category)
    rankings = team_service.rankings(season, team)
    ranked = next(
        (row for row in rankings if int(row["id"]) == int(shooter["id"])),
        None,
    )

    events = event_history(database, shooter["id"], season, 100)
    disciplines = discipline_progress(database, shooter["id"], season)
    recent = {
        discipline: rolling_event_average(events, discipline, 500)
        for discipline in DISCIPLINES
    }

    eligibility = season_row["eligibility"]
    return {
        "found": True,
        "has_stats": True,
        "shooter": shooter,
        "team": team,
        "season_row": season_row,
        "ranking": ranked,
        "eligible": eligibility.eligible,
        "eligibility_reasons": list(eligibility.reasons),
        "events": events,
        "disciplines": disciplines,
        "recent_500_average": recent,
    }
