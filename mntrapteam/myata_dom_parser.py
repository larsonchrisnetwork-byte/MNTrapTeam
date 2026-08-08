from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re


@dataclass
class OfficialSeasonTotals:
    singles_targets: int = 0
    singles_hits: int = 0
    handicap_targets: int = 0
    handicap_hits: int = 0
    doubles_targets: int = 0
    doubles_hits: int = 0

    @property
    def singles_average(self) -> float:
        return (
            self.singles_hits / self.singles_targets * 100.0
            if self.singles_targets else 0.0
        )

    @property
    def handicap_average(self) -> float:
        return (
            self.handicap_hits / self.handicap_targets * 100.0
            if self.handicap_targets else 0.0
        )

    @property
    def doubles_average(self) -> float:
        return (
            self.doubles_hits / self.doubles_targets * 100.0
            if self.doubles_targets else 0.0
        )


def _integer(value: Any) -> int:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def parse_year_summary_row(cells: list[str]) -> dict[str, Any]:
    """Parse a MyATA yearly summary row.

    Layout observed:
    Year,
    Singles non-league Shot, Hit %,
    Singles league Shot, Hit %,
    Handicap Shot, Hit %,
    Doubles non-league Shot, Hit %,
    Doubles league Shot, Hit %
    """
    if len(cells) < 9:
        raise ValueError("Year summary row has too few cells")

    def pct(value: str) -> float:
        text = str(value or "").strip().replace("%", "")
        return float(text) if text else 0.0

    return {
        "year": str(cells[0]).strip(),
        "singles_targets": _integer(cells[1]),
        "singles_pct": pct(cells[2]),
        "handicap_targets": _integer(cells[5]),
        "handicap_pct": pct(cells[6]),
        "doubles_targets": _integer(cells[7]),
        "doubles_pct": pct(cells[8]),
    }


def parse_score_detail_rows(rows: list[list[str]]) -> OfficialSeasonTotals:
    """Sum exact targets SHOT AT and HIT from MyATA 2026 Score Details.

    Observed columns:
    #, Date, Club,
    Singles Shot, Singles Hit, Singles League Shot, Singles League Hit,
    Handicap Yds, Prev, Handicap Shot, Handicap Hit, Earn,
    Doubles Shot, Doubles Hit, Doubles League Shot, Doubles League Hit.
    """
    totals = OfficialSeasonTotals()

    for cells in rows:
        if len(cells) < 14:
            continue

        first = str(cells[0]).strip().lower()
        if first in {"#", "", "2026 score details"}:
            continue

        # Require a plausible shoot/date row.
        if not re.search(r"\d", str(cells[1] if len(cells) > 1 else "")):
            continue

        totals.singles_targets += _integer(cells[3])
        totals.singles_hits += _integer(cells[4])

        totals.handicap_targets += _integer(cells[9])
        totals.handicap_hits += _integer(cells[10])

        totals.doubles_targets += _integer(cells[12])
        totals.doubles_hits += _integer(cells[13])

    return totals


def validate_detail_against_summary(
    totals: OfficialSeasonTotals,
    summary: dict[str, Any],
) -> list[str]:
    warnings = []

    pairs = (
        ("Singles", totals.singles_targets, summary["singles_targets"]),
        ("Handicap", totals.handicap_targets, summary["handicap_targets"]),
        ("Doubles", totals.doubles_targets, summary["doubles_targets"]),
    )

    for label, detail_targets, summary_targets in pairs:
        if detail_targets != summary_targets:
            warnings.append(
                f"{label} detail targets {detail_targets} != "
                f"summary targets {summary_targets}"
            )

    return warnings
