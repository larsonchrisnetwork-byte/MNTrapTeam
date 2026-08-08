from __future__ import annotations

import argparse

from .database import Database
from .paths import DATA
from .zone_haa_live import discover_2026_zone_shoots, pending_zone_residency, sync_zone_haa


def main():
    parser = argparse.ArgumentParser(
        description="Discover and sync 2026 Minnesota Zone HAA results"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover")
    discover.add_argument("--start-id", type=int, default=2000)
    discover.add_argument("--end-id", type=int, default=2100)

    sync = sub.add_parser("sync")
    sync.add_argument(
        "--zone",
        choices=["SOUTHERN", "CENTRAL", "NORTHERN"],
        required=True,
    )
    sync.add_argument("--shoot-id", type=int, required=True)
    sync.add_argument("--season", type=int, default=2026)

    pending = sub.add_parser("pending")
    pending.add_argument("--season", type=int, default=2026)

    args = parser.parse_args()
    db = Database(DATA / "mntrapteam.db")

    if args.command == "discover":
        found = discover_2026_zone_shoots(args.start_id, args.end_id)
        if not found:
            print("No 2026 Minnesota Zone shoots found in that ID range.")
            return 1
        for item in found:
            print(
                f"{item.zone}: shootid={item.shoot_id} | "
                f"{item.start_date} | {item.name}"
            )
        return 0

    if args.command == "sync":
        result = sync_zone_haa(db, args.shoot_id, args.zone, args.season)
        print(f"Shoot: {result.shoot_name}")
        print(f"Zone: {result.zone}")
        print(f"Score rows imported: {result.imported_score_rows}")
        print(f"HAA target completers: {result.haa_completers}")
        print(f"Qualified resident-zone matches: {result.qualified_resident_zone}")
        print(f"Resident zone still unverified: {result.resident_zone_unverified}")
        print(f"Completed wrong resident zone: {result.wrong_resident_zone}")
        for warning in result.warnings[:20]:
            print(f"WARNING: {warning}")
        return 0

    rows = pending_zone_residency(db, args.season)
    if not rows:
        print("No Zone HAA completers are waiting for resident-zone verification.")
        return 0

    for row in rows:
        ata = row["ata_number"] or "(ATA unknown)"
        print(
            f"{row['shoot_zone']:8} | {ata:12} | "
            f"{row['display_name']} | {row['shoot_name']}"
        )
    print()
    print(f"Pending resident-zone verification: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
