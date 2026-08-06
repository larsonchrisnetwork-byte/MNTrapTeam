from __future__ import annotations

from typing import Any
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
        shoot_number = str(row.get("ShootNumber") or "")
        event_date = str(row.get("Date") or "")
        shoot_name = str(row.get("Name") or "")
        for discipline, target_field, hit_field in mappings:
            targets = int(row.get(target_field) or 0)
            if not targets:
                continue
            observe_event(
                database,
                shooter_id=shooter_id,
                season=season,
                event_date=event_date,
                shoot_name=shoot_name,
                discipline=discipline,
                targets=targets,
                hits=int(row.get(hit_field) or 0),
                source="myata",
                source_record_id=f"{shoot_number}:{event_date}:{discipline}",
                shoot_number=shoot_number,
                club=shoot_name,
                state="",
                official=True,
            )
            imported += 1
    return imported
