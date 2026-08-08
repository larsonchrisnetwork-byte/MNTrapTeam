from __future__ import annotations

import argparse

from .database import Database
from .paths import DATA


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove only provisional Recent Score Scout rows for one shoot."
    )
    parser.add_argument("shoot_id", type=int)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete; without --yes this is preview only.",
    )
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")

    shoots = db.query(
        "SELECT id,name,start_date FROM shoots WHERE source_url LIKE ? OR id=?",
        (f"%shootid={args.shoot_id}%", args.shoot_id),
    )
    if not shoots:
        print(f"No local shoot record found for ShootScoreBoard shootid {args.shoot_id}.")
        return 0

    local_ids = [int(r["id"]) for r in shoots]
    placeholders = ",".join("?" for _ in local_ids)

    rows = db.query(
        f"""
        SELECT sc.id, sc.shooter_id, sc.event_name, sc.discipline,
               sc.targets, sc.hits, s.display_name
        FROM scores sc
        LEFT JOIN shooters s ON s.id=sc.shooter_id
        WHERE sc.shoot_id IN ({placeholders})
          AND sc.source='ShootScoreBoard recent-scout'
          AND COALESCE(sc.official,0)=0
        ORDER BY sc.id
        """,
        tuple(local_ids),
    )

    print("MNTrapTeam Provisional Scout Cleanup")
    print("====================================")
    print(f"ShootScoreBoard shootid: {args.shoot_id}")
    print(f"Provisional recent-scout rows found: {len(rows)}")
    for r in rows:
        print(
            f"{r['id']} | {r['display_name']} | {r['event_name']} | "
            f"{r['discipline']} {r['hits']}/{r['targets']}"
        )

    if not args.yes:
        print()
        print("PREVIEW ONLY. Re-run with --yes to delete these provisional rows.")
        return 0

    if rows:
        ids = [int(r["id"]) for r in rows]
        marks = ",".join("?" for _ in ids)
        db.execute(f"DELETE FROM scores WHERE id IN ({marks})", tuple(ids))

    print()
    print(f"Deleted provisional rows: {len(rows)}")
    print("Official MyATA data was not touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
