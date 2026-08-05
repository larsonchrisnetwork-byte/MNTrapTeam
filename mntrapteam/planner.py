from __future__ import annotations

from copy import deepcopy
from typing import Any

from .calculations import DISCIPLINES, hoa, project, team_rankings


def project_plan(row: dict[str, Any], additions: dict[str, tuple[int, float]]) -> dict[str, Any]:
    projected = deepcopy(row)
    details: dict[str, dict[str, float | int]] = {}

    for discipline in DISCIPLINES:
        new_targets, expected_average = additions.get(discipline, (0, 0.0))
        result = project(
            int(row.get(f"{discipline}_hits", 0) or 0),
            int(row.get(f"{discipline}_targets", 0) or 0),
            int(new_targets),
            float(expected_average),
        )
        projected[f"{discipline}_hits"] = result["hits"]
        projected[f"{discipline}_targets"] = result["targets"]
        projected[f"{discipline}_average"] = result["average"]
        details[discipline] = result

    projected["hoa"] = hoa(projected)
    projected["projection_details"] = details
    return projected


def projected_team_rank(rows, shooter_id, additions, rules_engine, team):
    updated = []
    found = False
    for row in rows:
        candidate = dict(row)
        if int(candidate.get("id") or 0) == int(shooter_id):
            candidate = project_plan(candidate, additions)
            found = True
        updated.append(candidate)

    if not found:
        raise ValueError(f"Shooter id {shooter_id} was not found")

    rankings = team_rankings(updated, rules_engine, team)
    ranked = next(
        (item for item in rankings if int(item.get("id") or 0) == int(shooter_id)),
        None,
    )
    if ranked is None:
        raise ValueError("Shooter is not assigned to the selected team")

    return {
        "shooter": ranked,
        "rankings": rankings,
        "rank": ranked["rank"],
        "eligible_rank": ranked.get("eligible_rank"),
        "selected": ranked["selected"],
        "hoa": ranked["hoa"],
        "cut_line_hoa": ranked.get("cut_line_hoa"),
        "hoa_gap_to_cut": ranked.get("hoa_gap_to_cut"),
    }


def required_uniform_average_for_cut(
    rows,
    shooter_id,
    future_targets,
    rules_engine,
    team,
    precision=0.01,
):
    def outcome(expected_average):
        additions = {
            discipline: (int(future_targets.get(discipline, 0)), expected_average)
            for discipline in DISCIPLINES
        }
        return projected_team_rank(
            rows, shooter_id, additions, rules_engine, team
        )

    if outcome(0.0)["selected"]:
        return 0.0
    if not outcome(100.0)["selected"]:
        return None

    low, high = 0.0, 100.0
    while high - low > precision:
        midpoint = (low + high) / 2.0
        if outcome(midpoint)["selected"]:
            high = midpoint
        else:
            low = midpoint
    return round(high, 2)
