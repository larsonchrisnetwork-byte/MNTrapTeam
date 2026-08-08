from __future__ import annotations

from collections import defaultdict

from .database import Database
from .identity import normalize_ata, normalize_person_name
from .paths import DATA


def _rows(db, sql, params=()):
    return [dict(r) for r in db.query(sql, params)]


def _score_signature(row):
    keys = (
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
    return tuple((k, row.get(k)) for k in keys if k in row)


def _table_columns(db, table):
    safe = table.replace('"', '""')
    return [dict(r)["name"] for r in db.query(f'PRAGMA table_info("{safe}")')]


def _insert_row(db, table, row, exclude=()):
    cols = [
        key for key in row.keys()
        if key not in set(exclude)
    ]
    safe_table = table.replace('"', '""')
    col_sql = ",".join(f'"{c.replace(chr(34), chr(34)*2)}"' for c in cols)
    placeholders = ",".join("?" for _ in cols)
    values = tuple(row[c] for c in cols)

    db.execute(
        f'INSERT INTO "{safe_table}" ({col_sql}) VALUES ({placeholders})',
        values,
    )


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    shooters = _rows(
        db,
        "SELECT id, ata_number, display_name FROM shooters ORDER BY id",
    )

    by_name = defaultdict(list)
    for shooter in shooters:
        key = normalize_person_name(shooter.get("display_name"))
        if key:
            by_name[key].append(shooter)

    pairs = []
    for name, items in by_name.items():
        blank = [i for i in items if not normalize_ata(i.get("ata_number"))]
        numbered = [i for i in items if normalize_ata(i.get("ata_number"))]
        if len(blank) == 1 and len(numbered) == 1:
            pairs.append((name, blank[0], numbered[0]))

    print("MNTrapTeam Blank-ATA Migration")
    print("==============================")
    print(f"Pairs to migrate: {len(pairs)}")
    print()

    migrated_pairs = 0

    for name, orphan, target in pairs:
        orphan_id = int(orphan["id"])
        target_id = int(target["id"])

        print(name)
        print(
            f"  orphan id={orphan_id} -> "
            f"target id={target_id} ATA {normalize_ata(target['ata_number'])}"
        )

        # Move unique scores.
        orphan_scores = _rows(
            db,
            "SELECT * FROM scores WHERE shooter_id=? ORDER BY id",
            (orphan_id,),
        )
        target_scores = _rows(
            db,
            "SELECT * FROM scores WHERE shooter_id=? ORDER BY id",
            (target_id,),
        )
        target_sigs = {_score_signature(r) for r in target_scores}

        moved_scores = 0
        duplicate_scores = 0

        for row in orphan_scores:
            sig = _score_signature(row)

            if sig in target_sigs:
                duplicate_scores += 1
                continue

            cols = _table_columns(db, "scores")
            row_to_insert = {
                key: value
                for key, value in row.items()
                if key in cols
            }
            row_to_insert["shooter_id"] = target_id

            _insert_row(
                db,
                "scores",
                row_to_insert,
                exclude=("id",),
            )
            moved_scores += 1

        # Move season_stats only when target does not already have that season.
        orphan_stats = _rows(
            db,
            "SELECT * FROM season_stats WHERE shooter_id=?",
            (orphan_id,),
        )
        target_stats = _rows(
            db,
            "SELECT * FROM season_stats WHERE shooter_id=?",
            (target_id,),
        )
        target_seasons = {r.get("season") for r in target_stats}

        moved_stats = 0
        skipped_stats = 0

        for row in orphan_stats:
            season = row.get("season")
            if season in target_seasons:
                skipped_stats += 1
                continue

            cols = _table_columns(db, "season_stats")
            row_to_insert = {
                key: value
                for key, value in row.items()
                if key in cols
            }
            row_to_insert["shooter_id"] = target_id

            _insert_row(
                db,
                "season_stats",
                row_to_insert,
                exclude=("id",),
            )
            moved_stats += 1

        # Delete orphan-linked rows only after safe copies/skips are complete.
        db.execute(
            "DELETE FROM scores WHERE shooter_id=?",
            (orphan_id,),
        )
        db.execute(
            "DELETE FROM season_stats WHERE shooter_id=?",
            (orphan_id,),
        )

        # Refuse deletion if any known shooter references remain.
        remaining = 0
        for table in ("scores", "season_stats", "haa_qualifications",
                      "score_observations", "myata_mn_enrichment"):
            try:
                cols = _table_columns(db, table)
            except Exception:
                continue
            if "shooter_id" not in cols:
                continue
            n = _rows(
                db,
                f'SELECT COUNT(*) AS n FROM "{table}" WHERE shooter_id=?',
                (orphan_id,),
            )
            if n:
                remaining += int(n[0]["n"])

        if remaining:
            raise RuntimeError(
                f"Refusing to delete orphan id={orphan_id}; "
                f"{remaining} references remain"
            )

        db.execute(
            "DELETE FROM shooters WHERE id=?",
            (orphan_id,),
        )

        print(
            f"  scores moved={moved_scores}, "
            f"duplicates skipped={duplicate_scores}"
        )
        print(
            f"  season_stats moved={moved_stats}, "
            f"same-season skipped={skipped_stats}"
        )
        print("  orphan shooter deleted.")
        print()

        migrated_pairs += 1

    print(f"Migrated pairs: {migrated_pairs}")
    print("Migration complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
