from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import hashlib


SOURCE_PRIORITY = {
    "manual": 10,
    "shootscoreboard": 40,
    "sosclays": 50,
    "ata_scores": 60,
    "myata": 100,
}

STATUS_PROVISIONAL = "PROVISIONAL"
STATUS_OFFICIAL = "OFFICIAL"
STATUS_RECONCILED = "RECONCILED"
STATUS_DISPUTED = "DISPUTED"


@dataclass(frozen=True)
class ScoreObservation:
    shooter_id: int
    season: int
    event_date: str
    shoot_name: str
    discipline: str
    targets: int
    hits: int
    source: str
    source_record_id: str = ""
    shoot_number: str = ""
    event_name: str = ""
    club: str = ""
    state: str = ""
    in_state: bool = False
    source_url: str = ""
    official: bool = False
    imported_at: str = ""

    @property
    def normalized_source(self) -> str:
        return self.source.strip().lower().replace(" ", "_")


def ensure_schema(database) -> None:
    database.execute("""
        CREATE TABLE IF NOT EXISTS score_observations(
            id INTEGER PRIMARY KEY,
            shooter_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            shoot_name TEXT NOT NULL,
            shoot_number TEXT NOT NULL DEFAULT '',
            event_name TEXT NOT NULL DEFAULT '',
            discipline TEXT NOT NULL CHECK(
                discipline IN ('singles','handicap','doubles')
            ),
            targets INTEGER NOT NULL CHECK(targets>=0),
            hits INTEGER NOT NULL CHECK(hits>=0 AND hits<=targets),
            club TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT '',
            in_state INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            source_record_id TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            official INTEGER NOT NULL DEFAULT 0,
            observation_key TEXT NOT NULL UNIQUE,
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE
        )
    """)
    database.execute("""
        CREATE INDEX IF NOT EXISTS idx_observations_shooter_season
        ON score_observations(shooter_id,season)
    """)
    database.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_audit(
            id INTEGER PRIMARY KEY,
            shooter_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            match_key TEXT NOT NULL,
            status TEXT NOT NULL,
            selected_observation_id INTEGER,
            provisional_observation_id INTEGER,
            official_observation_id INTEGER,
            detail TEXT NOT NULL DEFAULT '',
            reconciled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(shooter_id,season,match_key),
            FOREIGN KEY(shooter_id) REFERENCES shooters(id) ON DELETE CASCADE
        )
    """)


def observation_key(observation: ScoreObservation) -> str:
    if observation.source_record_id:
        raw = (
            f"{observation.normalized_source}|"
            f"{observation.source_record_id}|"
            f"{observation.discipline}"
        )
    else:
        raw = "|".join((
            observation.normalized_source,
            str(observation.shooter_id),
            observation.event_date,
            observation.shoot_number,
            observation.shoot_name.strip().upper(),
            observation.event_name.strip().upper(),
            observation.discipline,
            str(observation.targets),
            str(observation.hits),
        ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def match_key(row: dict[str, Any]) -> str:
    shoot_number = str(row.get("shoot_number") or "").strip()
    location = (
        f"NUMBER:{shoot_number}"
        if shoot_number
        else "NAME:" + str(row.get("shoot_name") or "").strip().upper()
    )
    return "|".join((
        str(row["shooter_id"]),
        str(row["event_date"]),
        location,
        str(row["discipline"]),
    ))


def store_observation(database, observation: ScoreObservation) -> int:
    ensure_schema(database)
    source = observation.normalized_source
    if source not in SOURCE_PRIORITY:
        raise ValueError(f"Unknown score source: {observation.source}")
    if observation.discipline not in {"singles", "handicap", "doubles"}:
        raise ValueError("Invalid discipline")
    if observation.hits < 0 or observation.hits > observation.targets:
        raise ValueError("hits must be between zero and targets")

    key = observation_key(observation)
    database.execute("""
        INSERT INTO score_observations(
            shooter_id,season,event_date,shoot_name,shoot_number,event_name,
            discipline,targets,hits,club,state,in_state,source,
            source_record_id,source_url,official,observation_key,imported_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,COALESCE(NULLIF(?,''),CURRENT_TIMESTAMP))
        ON CONFLICT(observation_key) DO UPDATE SET
            targets=excluded.targets,
            hits=excluded.hits,
            club=excluded.club,
            state=excluded.state,
            in_state=excluded.in_state,
            source_url=excluded.source_url,
            official=excluded.official,
            imported_at=excluded.imported_at
    """, (
        observation.shooter_id,
        observation.season,
        observation.event_date,
        observation.shoot_name,
        observation.shoot_number,
        observation.event_name,
        observation.discipline,
        observation.targets,
        observation.hits,
        observation.club,
        observation.state.upper(),
        int(observation.in_state),
        source,
        observation.source_record_id,
        observation.source_url,
        int(observation.official),
        key,
        observation.imported_at,
    ))
    return database.query(
        "SELECT id FROM score_observations WHERE observation_key=?",
        (key,),
    )[0]["id"]


def _priority(row: dict[str, Any]) -> tuple[int, int, str]:
    source = str(row.get("source") or "").lower()
    return (
        int(bool(row.get("official"))),
        SOURCE_PRIORITY.get(source, 0),
        str(row.get("imported_at") or ""),
    )


def reconcile_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("rows cannot be empty")

    official = [row for row in rows if row.get("official")]
    provisional = [row for row in rows if not row.get("official")]
    selected = max(rows, key=_priority)

    status = STATUS_OFFICIAL if official else STATUS_PROVISIONAL
    detail = ""
    official_row = max(official, key=_priority) if official else None
    provisional_row = max(provisional, key=_priority) if provisional else None

    if official_row and provisional_row:
        official_score = (int(official_row["targets"]), int(official_row["hits"]))
        provisional_score = (
            int(provisional_row["targets"]),
            int(provisional_row["hits"]),
        )
        if official_score == provisional_score:
            status = STATUS_RECONCILED
            detail = (
                f"{provisional_row['source']} matched official "
                f"{official_row['source']}"
            )
        else:
            status = STATUS_DISPUTED
            detail = (
                f"Provisional {provisional_row['targets']}/"
                f"{provisional_row['hits']} from {provisional_row['source']} "
                f"differs from official {official_row['targets']}/"
                f"{official_row['hits']} from {official_row['source']}"
            )
        selected = official_row

    return {
        "match_key": match_key(selected),
        "status": status,
        "selected": selected,
        "official": official_row,
        "provisional": provisional_row,
        "detail": detail,
        "observation_count": len(rows),
    }


def reconciled_events(database, shooter_id: int, season: int) -> list[dict[str, Any]]:
    ensure_schema(database)
    rows = database.query("""
        SELECT * FROM score_observations
        WHERE shooter_id=? AND season=?
        ORDER BY event_date,id
    """, (shooter_id, season))
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(match_key(row), []).append(row)

    output = []
    for key in sorted(groups):
        result = reconcile_group(groups[key])
        selected = dict(result["selected"])
        selected.update({
            "reconciliation_status": result["status"],
            "reconciliation_detail": result["detail"],
            "observation_count": result["observation_count"],
            "has_official": result["official"] is not None,
            "has_provisional": result["provisional"] is not None,
        })
        output.append(selected)
    return output


def totals_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        discipline: {"targets": 0, "hits": 0}
        for discipline in ("singles", "handicap", "doubles")
    }
    status_counts = {
        STATUS_PROVISIONAL: 0,
        STATUS_OFFICIAL: 0,
        STATUS_RECONCILED: 0,
        STATUS_DISPUTED: 0,
    }
    for event in events:
        item = totals[event["discipline"]]
        item["targets"] += int(event["targets"])
        item["hits"] += int(event["hits"])
        status = event.get("reconciliation_status", STATUS_PROVISIONAL)
        status_counts[status] = status_counts.get(status, 0) + 1

    for item in totals.values():
        item["average"] = (
            item["hits"] / item["targets"] * 100
            if item["targets"] else 0.0
        )
    return {
        "disciplines": totals,
        "status_counts": status_counts,
        "total_targets": sum(item["targets"] for item in totals.values()),
    }


def live_totals(database, shooter_id: int, season: int) -> dict[str, Any]:
    events = reconciled_events(database, shooter_id, season)
    result = totals_from_events(events)
    result["events"] = events
    result["view"] = "LIVE"
    return result


def official_totals(database, shooter_id: int, season: int) -> dict[str, Any]:
    ensure_schema(database)
    rows = database.query("""
        SELECT * FROM score_observations
        WHERE shooter_id=? AND season=? AND official=1
        ORDER BY event_date,id
    """, (shooter_id, season))
    result = totals_from_events(rows)
    result["events"] = rows
    result["view"] = "OFFICIAL"
    return result


def pending_official(database, shooter_id: int, season: int) -> dict[str, Any]:
    events = reconciled_events(database, shooter_id, season)
    pending = [
        event for event in events
        if event["reconciliation_status"] == STATUS_PROVISIONAL
    ]
    disputed = [
        event for event in events
        if event["reconciliation_status"] == STATUS_DISPUTED
    ]
    return {
        "pending_events": pending,
        "disputed_events": disputed,
        "pending_targets": sum(int(event["targets"]) for event in pending),
        "disputed_targets": sum(int(event["targets"]) for event in disputed),
    }


def rebuild_live_season_stats(database, shooter_id: int, season: int) -> None:
    totals = live_totals(database, shooter_id, season)["disciplines"]
    database.upsert_stats(
        shooter_id,
        season,
        singles_targets=totals["singles"]["targets"],
        singles_hits=totals["singles"]["hits"],
        handicap_targets=totals["handicap"]["targets"],
        handicap_hits=totals["handicap"]["hits"],
        doubles_targets=totals["doubles"]["targets"],
        doubles_hits=totals["doubles"]["hits"],
        source="reconciled_live",
        official=0,
    )
