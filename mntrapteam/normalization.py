from __future__ import annotations

from datetime import datetime
import re


SHOOT_ALIASES = {
    "MINNESOTA TRAP ASSN": "MINNESOTA STATE SHOOT",
    "MINNESOTA TRAP ASSOCIATION": "MINNESOTA STATE SHOOT",
    "MN STATE SHOOT": "MINNESOTA STATE SHOOT",
    "2026 MN STATE SHOOT": "MINNESOTA STATE SHOOT",
    "DEL-TONE SHOOTING RANGE": "DEL-TONE SHOOTING RANGE",
    "DEL TONE SHOOTING RANGE": "DEL-TONE SHOOTING RANGE",
    "ALEXANDRIA SHOOTING PARK": "ALEXANDRIA SHOOTING PARK",
    "LESTER PRAIRIE SPORTSMENS CLUB": "LESTER PRAIRIE SPORTSMENS CLUB",
    "LESTER PRAIRIE SPORTSMEN'S CLUB": "LESTER PRAIRIE SPORTSMENS CLUB",
    "OWATONNA GUN CLUB": "OWATONNA GUN CLUB",
    "BUFFALO GUN CLUB": "BUFFALO GUN CLUB",
    "UTAH TRAPSHOOTING ASSOC": "UTAH TRAPSHOOTING ASSOC",
}


def normalize_event_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    # Handles ISO timestamps with timezone suffixes.
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        raise ValueError(f"Unrecognized event date: {value!r}")


def normalize_shoot_name(value: str) -> str:
    text = " ".join(str(value or "").upper().replace("&", " AND ").split())
    text = re.sub(r"[.,]", "", text)
    text = text.replace("SPORTSMEN S", "SPORTSMENS")
    return SHOOT_ALIASES.get(text, text)


def inferred_state(shoot_name: str) -> str:
    normalized = normalize_shoot_name(shoot_name)
    if normalized in {
        "MINNESOTA STATE SHOOT",
        "DEL-TONE SHOOTING RANGE",
        "ALEXANDRIA SHOOTING PARK",
        "LESTER PRAIRIE SPORTSMENS CLUB",
        "OWATONNA GUN CLUB",
        "BUFFALO GUN CLUB",
    }:
        return "MN"
    if normalized == "UTAH TRAPSHOOTING ASSOC":
        return "UT"
    return ""


def canonical_match_parts(
    event_date: str,
    shoot_name: str,
    shoot_number: str = "",
) -> tuple[str, str, str]:
    return (
        normalize_event_date(event_date),
        normalize_shoot_name(shoot_name),
        str(shoot_number or "").strip(),
    )
