from __future__ import annotations

from typing import Any


def race_summary(rankings: list[dict[str, Any]], team_size: int) -> dict[str, Any]:
    eligible = [row for row in rankings if row.get("eligible")]
    selected = [row for row in rankings if row.get("selected")]
    cut_line = selected[-1].get("hoa") if len(selected) == team_size else None

    return {
        "tracked": len(rankings),
        "eligible": len(eligible),
        "selected": len(selected),
        "team_size": team_size,
        "open_positions": max(0, team_size - len(selected)),
        "cut_line_hoa": cut_line,
    }


def classify_race_status(
    row: dict[str, Any],
    cut_line: float | None,
    bubble_width: float = 0.75,
) -> str:
    if row.get("selected"):
        return "On Team"
    if not row.get("eligible"):
        if cut_line is not None and float(row.get("hoa") or 0) >= cut_line - bubble_width:
            return "Bubble — Ineligible"
        return "Not Eligible"
    if cut_line is None:
        return "Eligible — Open Spot"

    gap = float(row.get("hoa") or 0) - cut_line
    if gap >= 0:
        return "On Team"
    if gap >= -bubble_width:
        return "Bubble"
    return "Outside Bubble"


def team_race(
    rankings: list[dict[str, Any]],
    team_size: int,
    bubble_width: float = 0.75,
    include_outside: int = 5,
) -> dict[str, Any]:
    if team_size <= 0:
        raise ValueError("team_size must be positive")
    if bubble_width < 0:
        raise ValueError("bubble_width cannot be negative")
    if include_outside < 0:
        raise ValueError("include_outside cannot be negative")

    summary = race_summary(rankings, team_size)
    cut_line = summary["cut_line_hoa"]
    rows: list[dict[str, Any]] = []
    outside_added = 0

    for source in rankings:
        row = dict(source)
        hoa = float(row.get("hoa") or 0)
        gap = None if cut_line is None else hoa - cut_line
        status = classify_race_status(row, cut_line, bubble_width)

        include = bool(row.get("selected"))
        if not include and cut_line is None:
            include = bool(row.get("eligible"))
        if not include and cut_line is not None and gap is not None:
            include = gap >= -bubble_width

        if not include and row.get("eligible") and outside_added < include_outside:
            include = True
            outside_added += 1

        if not include:
            continue

        row["race_status"] = status
        row["cut_line_hoa"] = cut_line
        row["hoa_gap_to_cut"] = gap
        row["birds_per_300_gap"] = None if gap is None else gap * 3.0
        row["needs_eligibility"] = not bool(row.get("eligible"))
        rows.append(row)

    return {
        "summary": summary,
        "rows": rows,
        "bubble_width": bubble_width,
    }


def shooter_race_position(
    rankings: list[dict[str, Any]],
    shooter_id: int,
    team_size: int,
    bubble_width: float = 0.75,
) -> dict[str, Any] | None:
    race = team_race(rankings, team_size, bubble_width, include_outside=len(rankings))
    return next(
        (
            row
            for row in race["rows"]
            if int(row.get("id") or 0) == int(shooter_id)
        ),
        None,
    )
