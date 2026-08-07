from __future__ import annotations

from typing import Any

from .normalization import (
    inferred_state,
    normalize_event_date,
    normalize_shoot_name,
)
from .reconciliation import ScoreObservation, store_observation


def source_name(value: str) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "shootscoreboard web": "shootscoreboard",
        "shootscoreboard": "shootscoreboard",
        "sos clays": "sosclays",
        "sosclays": "sosclays",
        "ata scores": "ata_scores",
        "scores.shootata.com": "ata_scores",
        "myata": "myata",
        "shootata": "myata",
    }
    return aliases.get(normalized, normalized.replace(" ", "_"))


def observe_event(database, **kwargs) -> int:
    source = source_name(kwargs.pop("source"))
    official = kwargs.pop("official", None)
    if official is None:
        official = source == "myata"

    kwargs["event_date"] = normalize_event_date(kwargs["event_date"])
    kwargs["shoot_name"] = normalize_shoot_name(kwargs["shoot_name"])
    if not kwargs.get("state"):
        kwargs["state"] = inferred_state(kwargs["shoot_name"])
    if "in_state" not in kwargs:
        kwargs["in_state"] = kwargs.get("state") == "MN"

    return store_observation(
        database,
        ScoreObservation(source=source, official=bool(official), **kwargs),
    )


def observe_myata_details(
    database,
    shooter_id: int,
    season: int,
    rows: list[dict[str, Any]],
) -> int:
    imported = 0
    mappings = (
        ("singles", "SinglesShot", "SinglesHit"),
        ("handicap", "HandicapShot", "HandicapHit"),
        ("doubles", "DoublesShot", "DoublesHit"),
    )
    for row in rows:
        shoot_number = str(row.get("ShootNumber") or "").strip()
        event_date = normalize_event_date(str(row.get("Date") or ""))
        shoot_name = normalize_shoot_name(str(row.get("Name") or ""))
        state = str(row.get("State") or inferred_state(shoot_name)).upper()

        for discipline, target_field, hit_field in mappings:
            targets = int(row.get(target_field) or 0)
            if not targets:
                continue
            hits = int(row.get(hit_field) or 0)
            observe_event(
                database,
                shooter_id=shooter_id,
                season=season,
                event_date=event_date,
                shoot_name=shoot_name,
                discipline=discipline,
                targets=targets,
                hits=hits,
                source="myata",
                source_record_id=(
                    f"{shooter_id}:{season}:{shoot_number}:"
                    f"{event_date}:{discipline}"
                ),
                shoot_number=shoot_number,
                club=shoot_name,
                state=state,
                in_state=state == "MN",
                official=True,
            )
            imported += 1
    return imported
