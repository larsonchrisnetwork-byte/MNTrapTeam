def apply_projected_ranking(rows, team_size):
    ordered = sorted(
        rows,
        key=lambda row: (
            -float(row.get("live_hoa") or 0.0),
            str(row.get("display_name") or ""),
        ),
    )

    for rank, row in enumerate(ordered, 1):
        row["projected_rank"] = rank

    projected_cut = (
        float(ordered[team_size - 1].get("live_hoa") or 0.0)
        if len(ordered) >= team_size else None
    )

    eligible = [row for row in ordered if bool(row.get("eligible"))]
    for rank, row in enumerate(eligible, 1):
        row["eligible_rank"] = rank

    eligible_cut = (
        float(eligible[team_size - 1].get("live_hoa") or 0.0)
        if len(eligible) >= team_size else None
    )

    for row in ordered:
        row.setdefault("eligible_rank", None)
        row["projected_cut_hoa"] = projected_cut
        row["eligible_cut_hoa"] = eligible_cut
        row["gap_to_projected_cut"] = (
            float(row.get("live_hoa") or 0.0) - projected_cut
            if projected_cut is not None else None
        )
        row["projected_team"] = row["projected_rank"] <= team_size
        row["eligible_team_now"] = (
            bool(row.get("eligible"))
            and row["eligible_rank"] is not None
            and row["eligible_rank"] <= team_size
        )

    return {
        "rows": ordered,
        "projected_cut_hoa": projected_cut,
        "eligible_cut_hoa": eligible_cut,
    }
