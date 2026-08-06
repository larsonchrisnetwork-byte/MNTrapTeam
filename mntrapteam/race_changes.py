from __future__ import annotations

import json
from typing import Any


def _index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed = {}
    for row in rows:
        key = str(row.get("ata_number") or row.get("id") or row.get("display_name"))
        indexed[key] = row
    return indexed


def compare_rankings(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
    old = _index(previous)
    new = _index(current)
    all_keys = sorted(set(old) | set(new))
    changes = []

    for key in all_keys:
        before = old.get(key)
        after = new.get(key)

        if before is None:
            changes.append({
                "key": key,
                "display_name": after.get("display_name", ""),
                "change_type": "New shooter",
                "old_rank": None,
                "new_rank": after.get("rank"),
                "rank_change": None,
                "old_hoa": None,
                "new_hoa": after.get("hoa"),
                "hoa_change": None,
                "old_selected": False,
                "new_selected": bool(after.get("selected")),
                "team_change": "Entered team" if after.get("selected") else "",
            })
            continue

        if after is None:
            changes.append({
                "key": key,
                "display_name": before.get("display_name", ""),
                "change_type": "Removed shooter",
                "old_rank": before.get("rank"),
                "new_rank": None,
                "rank_change": None,
                "old_hoa": before.get("hoa"),
                "new_hoa": None,
                "hoa_change": None,
                "old_selected": bool(before.get("selected")),
                "new_selected": False,
                "team_change": "Left team" if before.get("selected") else "",
            })
            continue

        old_rank = before.get("rank")
        new_rank = after.get("rank")
        rank_change = (
            int(old_rank) - int(new_rank)
            if old_rank is not None and new_rank is not None
            else None
        )

        old_hoa = before.get("hoa")
        new_hoa = after.get("hoa")
        hoa_change = (
            float(new_hoa) - float(old_hoa)
            if old_hoa is not None and new_hoa is not None
            else None
        )

        old_selected = bool(before.get("selected"))
        new_selected = bool(after.get("selected"))
        team_change = ""
        if not old_selected and new_selected:
            team_change = "Entered team"
        elif old_selected and not new_selected:
            team_change = "Left team"

        if rank_change or team_change or (hoa_change and abs(hoa_change) >= 0.0001):
            changes.append({
                "key": key,
                "display_name": after.get("display_name", ""),
                "change_type": "Updated",
                "old_rank": old_rank,
                "new_rank": new_rank,
                "rank_change": rank_change,
                "old_hoa": old_hoa,
                "new_hoa": new_hoa,
                "hoa_change": hoa_change,
                "old_selected": old_selected,
                "new_selected": new_selected,
                "team_change": team_change,
            })

    changes.sort(
        key=lambda row: (
            0 if row.get("team_change") else 1,
            -(abs(row.get("rank_change") or 0)),
            str(row.get("display_name") or "").lower(),
        )
    )

    old_selected = {k for k, row in old.items() if row.get("selected")}
    new_selected = {k for k, row in new.items() if row.get("selected")}
    old_selected_rows = [row for row in previous if row.get("selected")]
    new_selected_rows = [row for row in current if row.get("selected")]
    old_cut = old_selected_rows[-1].get("hoa") if old_selected_rows else None
    new_cut = new_selected_rows[-1].get("hoa") if new_selected_rows else None

    return {
        "changes": changes,
        "entered_team": sorted(new_selected - old_selected),
        "left_team": sorted(old_selected - new_selected),
        "old_cut_line": old_cut,
        "new_cut_line": new_cut,
        "cut_line_change": (
            None
            if old_cut is None or new_cut is None
            else float(new_cut) - float(old_cut)
        ),
    }


def latest_team_snapshot(database, season: int, team: str) -> dict[str, Any] | None:
    rows = database.query(
        '''
        SELECT id, season, label, created_at, payload
        FROM snapshots
        WHERE season=?
        ORDER BY created_at DESC, id DESC
        ''',
        (season,),
    )
    for row in rows:
        try:
            payload = json.loads(row["payload"])
        except Exception:
            continue
        team_rows = payload.get(team)
        if isinstance(team_rows, list):
            return {
                "snapshot_id": row["id"],
                "label": row.get("label") or "",
                "created_at": row.get("created_at"),
                "rows": team_rows,
            }
    return None


def race_changes_from_latest_snapshot(database, team_service, season: int, team: str) -> dict[str, Any]:
    current = team_service.rankings(season, team)
    snapshot = latest_team_snapshot(database, season, team)

    if snapshot is None:
        return {
            "has_snapshot": False,
            "current": current,
            "changes": [],
            "message": "No saved snapshot is available for comparison.",
        }

    comparison = compare_rankings(snapshot["rows"], current)
    comparison.update({
        "has_snapshot": True,
        "snapshot_label": snapshot["label"],
        "snapshot_created_at": snapshot["created_at"],
        "current": current,
    })
    return comparison
