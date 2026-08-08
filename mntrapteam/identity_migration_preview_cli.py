from __future__ import annotations

from collections import defaultdict
from typing import Any

from .database import Database
from .identity import normalize_ata, normalize_person_name
from .paths import DATA


def _dict_rows(rows):
    return [dict(r) for r in rows]


def _columns(db, table):
    safe = table.replace('"', '""')
    return [dict(r)["name"] for r in db.query(f'PRAGMA table_info("{safe}")')]


def _rows_for(db, table, shooter_id):
    safe = table.replace('"', '""')
    cols = _columns(db, table)
    if "shooter_id" not in cols:
        return []
    return _dict_rows(
        db.query(
            f'SELECT * FROM "{safe}" WHERE shooter_id=? ORDER BY rowid',
            (shooter_id,),
        )
    )


def _season_key(row):
    return row.get("season")


def _score_signature(row):
    # Use stable business fields when present; ignore database ids/timestamps.
    candidates = (
        "season",
        "discipline",
        "shoot_date",
        "date",
        "club",
        "club_name",
        "shoot_name",
        "event_name",
        "targets",
        "hits",
        "source",
    )
    return tuple(
        (key, row.get(key))
        for key in candidates
        if key in row
    )


def _compact(row, keys):
    return {
        key: row.get(key)
        for key in keys
        if key in row
    }


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    shooters = _dict_rows(
        db.query(
            "SELECT id, ata_number, display_name FROM shooters ORDER BY id"
        )
    )

    by_name = defaultdict(list)
    for shooter in shooters:
        key = normalize_person_name(shooter.get("display_name"))
        if key:
            by_name[key].append(shooter)

    groups = []
    for key, items in by_name.items():
        blank = [
            item for item in items
            if not normalize_ata(item.get("ata_number"))
        ]
        numbered = [
            item for item in items
            if normalize_ata(item.get("ata_number"))
        ]
        if len(blank) == 1 and len(numbered) == 1:
            groups.append((key, blank[0], numbered[0]))

    print("MNTrapTeam Blank-ATA Migration Preview")
    print("======================================")
    print("NO DATABASE CHANGES WILL BE MADE.")
    print()

    safe_pairs = 0
    review_pairs = 0

    for name, orphan, target in groups:
        orphan_id = int(orphan["id"])
        target_id = int(target["id"])

        print(name)
        print(
            f"  ORPHAN   id={orphan_id} | ATA blank | "
            f"{orphan.get('display_name')}"
        )
        print(
            f"  TARGET   id={target_id} | "
            f"ATA {normalize_ata(target.get('ata_number'))} | "
            f"{target.get('display_name')}"
        )

        orphan_scores = _rows_for(db, "scores", orphan_id)
        target_scores = _rows_for(db, "scores", target_id)

        target_score_sigs = {
            _score_signature(row)
            for row in target_scores
        }
        new_scores = [
            row for row in orphan_scores
            if _score_signature(row) not in target_score_sigs
        ]
        duplicate_scores = len(orphan_scores) - len(new_scores)

        print(
            f"  scores: orphan={len(orphan_scores)} | "
            f"target={len(target_scores)} | "
            f"would-move={len(new_scores)} | "
            f"already-duplicate={duplicate_scores}"
        )

        for row in orphan_scores:
            print(
                "    orphan-score:",
                _compact(
                    row,
                    (
                        "id",
                        "season",
                        "discipline",
                        "shoot_date",
                        "date",
                        "club",
                        "club_name",
                        "shoot_name",
                        "event_name",
                        "targets",
                        "hits",
                        "source",
                    ),
                ),
            )

        orphan_stats = _rows_for(db, "season_stats", orphan_id)
        target_stats = _rows_for(db, "season_stats", target_id)

        target_by_season = {
            _season_key(row): row
            for row in target_stats
        }

        conflicts = []
        movable_stats = []

        for row in orphan_stats:
            season = _season_key(row)
            target_row = target_by_season.get(season)
            if target_row is None:
                movable_stats.append(row)
            else:
                conflicts.append((row, target_row))

        print(
            f"  season_stats: orphan={len(orphan_stats)} | "
            f"target={len(target_stats)} | "
            f"no-conflict={len(movable_stats)} | "
            f"same-season-conflicts={len(conflicts)}"
        )

        for orphan_row, target_row in conflicts:
            print(f"    CONFLICT season={orphan_row.get('season')}")
            print(
                "      orphan:",
                _compact(
                    orphan_row,
                    (
                        "season",
                        "singles_targets",
                        "singles_hits",
                        "handicap_targets",
                        "handicap_hits",
                        "doubles_targets",
                        "doubles_hits",
                        "mn_singles_targets",
                        "mn_handicap_targets",
                        "mn_doubles_targets",
                        "mn_clubs",
                        "source",
                    ),
                ),
            )
            print(
                "      target:",
                _compact(
                    target_row,
                    (
                        "season",
                        "singles_targets",
                        "singles_hits",
                        "handicap_targets",
                        "handicap_hits",
                        "doubles_targets",
                        "doubles_hits",
                        "mn_singles_targets",
                        "mn_handicap_targets",
                        "mn_doubles_targets",
                        "mn_clubs",
                        "source",
                    ),
                ),
            )

        if conflicts:
            print(
                "  STATUS: REVIEW — do not overwrite target season_stats."
            )
            review_pairs += 1
        else:
            print(
                "  STATUS: structurally safe to migrate orphan-linked rows."
            )
            safe_pairs += 1

        print()

    print("Summary")
    print("-------")
    print(f"Pairs structurally safe: {safe_pairs}")
    print(f"Pairs needing season_stats review: {review_pairs}")
    print()
    print(
        "Next migration policy will preserve the ATA-numbered official "
        "season_stats record whenever a same-season conflict exists."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
