from __future__ import annotations

import math

DISCIPLINES = ("singles", "handicap", "doubles")


def average(hits: int | float, targets: int | float) -> float:
    return (float(hits) / float(targets) * 100.0) if targets else 0.0


def hoa(row: dict) -> float:
    """MTA team HOA: arithmetic mean of singles, handicap and doubles averages."""
    return sum(
        average(row.get(f"{discipline}_hits", 0), row.get(f"{discipline}_targets", 0))
        for discipline in DISCIPLINES
    ) / 3.0


def project(hits: int, targets: int, new_targets: int, new_average: float) -> dict:
    if new_targets < 0 or not 0 <= new_average <= 100:
        raise ValueError("Invalid projection values")
    new_hits = round(new_targets * new_average / 100.0)
    total_hits = hits + new_hits
    total_targets = targets + new_targets
    return {
        "hits": total_hits,
        "targets": total_targets,
        "average": average(total_hits, total_targets),
        "added_hits": new_hits,
    }


def project_season(row: dict, additions: dict[str, tuple[int, float]]) -> dict:
    """Project one or more disciplines and return projected averages and HOA.

    additions example:
        {"singles": (300, 97.5), "doubles": (200, 95.0)}
    """
    result = dict(row)
    discipline_results: dict[str, dict] = {}

    for discipline in DISCIPLINES:
        new_targets, new_average = additions.get(discipline, (0, 0.0))
        projected = project(
            int(row.get(f"{discipline}_hits", 0) or 0),
            int(row.get(f"{discipline}_targets", 0) or 0),
            int(new_targets),
            float(new_average),
        )
        result[f"{discipline}_hits"] = projected["hits"]
        result[f"{discipline}_targets"] = projected["targets"]
        result[f"{discipline}_average"] = projected["average"]
        discipline_results[discipline] = projected

    result["hoa"] = hoa(result)
    result["disciplines"] = discipline_results
    return result


def targets_needed_for_average(
    hits: int,
    targets: int,
    goal: float,
    future_average: float,
    max_targets: int = 100000,
) -> int | None:
    if not 0 <= goal <= 100 or not 0 <= future_average <= 100:
        raise ValueError("Averages must be 0-100")
    if average(hits, targets) >= goal:
        return 0
    if future_average <= goal:
        return None

    required = math.ceil((goal * targets - 100 * hits) / (future_average - goal))
    required = max(0, required)
    return required if required <= max_targets else None


def average_needed_for_target(
    hits: int,
    targets: int,
    new_targets: int,
    goal_average: float,
) -> float | None:
    """Return the average needed on a fixed number of future targets.

    None means the requested goal is impossible even with 100% on all
    future targets.
    """
    if new_targets <= 0:
        raise ValueError("new_targets must be positive")
    if not 0 <= goal_average <= 100:
        raise ValueError("goal_average must be 0-100")

    required_hits = goal_average / 100.0 * (targets + new_targets) - hits
    needed = required_hits / new_targets * 100.0
    if needed > 100.0 + 1e-9:
        return None
    return max(0.0, needed)


def team_rankings(rows: list[dict], rules_engine, team: str) -> list[dict]:
    out = []
    for row in rows:
        category = row.get("category_declared") or row.get("category")
        if rules_engine.team_for_category(category) != team:
            continue
        eligibility = rules_engine.check(row, team)
        ranked = dict(row)
        ranked["hoa"] = hoa(row)
        ranked["eligible"] = eligibility.eligible
        ranked["eligibility_reasons"] = "; ".join(eligibility.reasons)
        out.append(ranked)

    out.sort(
        key=lambda item: (
            not item["eligible"],
            -item["hoa"],
            item.get("display_name", "").lower(),
        )
    )

    size = int(rules_engine.rules["teams"][team]["size"])
    eligible_position = 0
    for rank, item in enumerate(out, 1):
        item["rank"] = rank
        if item["eligible"]:
            eligible_position += 1
        item["eligible_rank"] = eligible_position if item["eligible"] else None
        item["selected"] = bool(item["eligible"] and eligible_position <= size)

    selected = [item for item in out if item["selected"]]
    cut_line = selected[-1]["hoa"] if len(selected) == size else None

    for item in out:
        item["cut_line_hoa"] = cut_line
        if cut_line is None:
            item["hoa_gap_to_cut"] = None
            item["birds_per_300_gap"] = None
        else:
            gap = item["hoa"] - cut_line
            item["hoa_gap_to_cut"] = gap
            # One HOA percentage point equals three birds per 300 HAA targets.
            item["birds_per_300_gap"] = gap * 3.0

    return out
