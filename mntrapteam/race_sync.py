from __future__ import annotations

import argparse
from pathlib import Path

from .current_race import (
    TARGET_YEAR,
    discover_current_minnesota_shoots,
    read_candidate_csv,
    sync_current_race,
    write_candidate_csv,
    write_sync_report,
)
from .database import Database
from .paths import DATA, EXPORTS


def database_path() -> Path:
    return DATA / "mntrapteam.db"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover and import Minnesota shoots for the active 2026 team race"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover", help="Create a reviewable shoot queue")
    discover.add_argument(
        "--output",
        default=str(EXPORTS / "2026_minnesota_shoot_queue.csv"),
    )

    sync = sub.add_parser("sync", help="Import selected shoots from the queue")
    sync.add_argument(
        "--queue",
        default=str(EXPORTS / "2026_minnesota_shoot_queue.csv"),
    )
    sync.add_argument("--threshold", type=int, default=88)
    sync.add_argument("--allow-out-of-season", action="store_true")
    sync.add_argument(
        "--report",
        default=str(EXPORTS / "2026_race_sync_report.json"),
    )

    args = parser.parse_args()

    if args.command == "discover":
        candidates = discover_current_minnesota_shoots()
        output = write_candidate_csv(candidates, Path(args.output))
        print(f"Target year: {TARGET_YEAR}")
        print(f"Discovered {len(candidates)} Minnesota shoots in the active target-year window.")
        print(f"Review queue: {output}")
        return 0

    candidates = read_candidate_csv(Path(args.queue))
    summary = sync_current_race(
        Database(database_path()),
        candidates,
        matcher_threshold=args.threshold,
        allow_out_of_season=args.allow_out_of_season,
    )
    report = write_sync_report(summary, Path(args.report))

    print(f"Attempted shoots: {summary.attempted}")
    print(f"Imported shoots: {summary.imported_shoots}")
    print(f"Duplicate shoots: {summary.duplicate_shoots}")
    print(f"Failed shoots: {summary.failed_shoots}")
    print(f"Score rows imported: {summary.score_rows_imported}")
    print(f"New shooter records: {summary.shooters_created}")
    print(f"Report: {report}")

    for item in summary.results:
        print(
            f"{item.status.upper()}: {item.shoot_id} {item.name} "
            f"({item.rows_imported}/{item.rows_found} rows)"
        )
        if item.error:
            print(f"  ERROR: {item.error}")
        for warning in item.warnings:
            print(f"  WARNING: {warning}")

    return 1 if summary.failed_shoots else 0


if __name__ == "__main__":
    raise SystemExit(main())
