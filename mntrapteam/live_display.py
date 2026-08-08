from __future__ import annotations

DISCIPLINE_LABELS = {
    "singles": "Singles",
    "handicap": "Handicap",
    "doubles": "Doubles",
}


def actionable_missing_requirements(progress, reasons=None):
    items = []

    for discipline in ("singles", "handicap", "doubles"):
        have, need = progress.get(discipline, (0, 0))
        shortage = max(0, int(need) - int(have))
        if shortage:
            items.append(
                f"Need {shortage:,} {DISCIPLINE_LABELS[discipline]} targets"
            )

    for discipline in ("singles", "handicap", "doubles"):
        have, need = progress.get(f"mn_{discipline}", (0, 0))
        shortage = max(0, int(need) - int(have))
        if shortage:
            items.append(
                f"Need {shortage:,} MN {DISCIPLINE_LABELS[discipline]} targets"
            )

    have, need = progress.get("clubs", (0, 0))
    shortage = max(0, int(need) - int(have))
    if shortage:
        word = "club" if shortage == 1 else "clubs"
        items.append(f"Need {shortage} MN {word}")

    have, need = progress.get("haa", (0, 0))
    if int(need) and int(have) < int(need):
        items.append("Need qualifying HAA")

    reason_list = [reasons] if isinstance(reasons, str) else list(reasons or [])
    if any("Not marked as a Minnesota resident" in r for r in reason_list):
        items.append("Not marked MN resident")

    return "Ready ✓" if not items else "; ".join(items)


def rank_by_live_hoa(rows, team_size):
    ordered = sorted(
        rows,
        key=lambda row: (
            -float(row.get("live_hoa") or 0.0),
            str(row.get("display_name") or "").upper(),
        ),
    )

    for rank, row in enumerate(ordered, 1):
        row["projected_rank"] = rank
        row["live_pool_rank"] = rank

    projected_cut = (
        float(ordered[team_size - 1].get("live_hoa") or 0.0)
        if len(ordered) >= team_size
        else None
    )

    eligible = [row for row in ordered if bool(row.get("eligible"))]
    for rank, row in enumerate(eligible, 1):
        row["eligible_rank"] = rank

    eligible_cut = (
        float(eligible[team_size - 1].get("live_hoa") or 0.0)
        if len(eligible) >= team_size
        else None
    )

    for row in ordered:
        row.setdefault("eligible_rank", None)
        row["projected_cut_hoa"] = projected_cut
        row["eligible_cut_hoa"] = eligible_cut
        row["live_cut_hoa"] = projected_cut
        row["live_gap_to_cut"] = (
            float(row.get("live_hoa") or 0.0) - projected_cut
            if projected_cut is not None
            else None
        )

    return {
        "rows": ordered,
        "projected_cut_hoa": projected_cut,
        "eligible_cut_hoa": eligible_cut,
    }
