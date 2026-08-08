from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def normalize_ata(value: Any) -> str:
    """Normalize ATA number without losing meaningful leading zeroes."""
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def normalize_person_name(value: Any) -> str:
    text = str(value or "").upper()
    text = re.sub(r"\b(JR|SR|II|III|IV)\.?\b", r" \1 ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class IdentityKey:
    ata_number: str
    display_name: str = ""

    @property
    def valid(self) -> bool:
        return bool(self.ata_number)


def identity_key(ata_number: Any, display_name: Any = "") -> IdentityKey:
    return IdentityKey(
        ata_number=normalize_ata(ata_number),
        display_name=str(display_name or "").strip(),
    )


def same_shooter(
    left_ata: Any,
    right_ata: Any,
) -> bool:
    """ATA number is the only authoritative shooter identity."""
    left = normalize_ata(left_ata)
    right = normalize_ata(right_ata)
    return bool(left and right and left == right)


def safe_identity_match(
    expected_ata: Any,
    candidate_ata: Any,
    *,
    expected_name: Any = "",
    candidate_name: Any = "",
) -> bool:
    """
    Return True only for an exact ATA-number match.

    Names are deliberately ignored for identity. They may be used by callers
    for display/debugging but never to merge or accept shooter records.
    """
    return same_shooter(expected_ata, candidate_ata)
