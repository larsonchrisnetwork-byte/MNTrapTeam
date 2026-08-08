from __future__ import annotations

import argparse
from pathlib import Path

from .database import Database
from .paths import DATA
from .sos_state_haa import (
    import_state_haa_report,
    latest_state_report_capture,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import 2026 Minnesota State HAA qualification from SOS"
    )
    parser.add_argument("--report")
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    report = Path(args.report) if args.report else latest_state_report_capture()
    database = Database(DATA / "mntrapteam.db")

    print(f"Using report: {report}")

    result = import_state_haa_report(
        database,
        report,
        season=args.season,
    )

    print(f"Report rows: {result.report_rows}")
    print(f"Minnesota rows: {result.minnesota_rows}")
    print(f"State HAA completers: {result.haa_completers}")
    print(f"Shooter matches/creates: {result.shooter_matches}")
    print(f"New shooter records: {result.shooter_creates}")
    print(f"HAA records written: {result.haa_records_written}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
