from __future__ import annotations

import argparse
import json
from pathlib import Path

from .database import Database
from .myata_capture import import_myata_capture, latest_capture
from .paths import CONFIG, DATA


def load_settings() -> dict:
    return json.loads(
        (CONFIG / "settings.json").read_text(encoding="utf-8-sig")
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import official MyATA JSON capture into reconciliation ledger"
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--capture")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--ata")
    args = parser.parse_args()

    settings = load_settings()
    database_path = Path(settings.get("database", "data/mntrapteam.db"))
    if not database_path.is_absolute():
        database_path = CONFIG.parent / database_path

    capture_root = DATA / "connector_downloads" / "myata"
    capture = (
        latest_capture(capture_root)
        if args.latest or not args.capture
        else Path(args.capture)
    )
    expected_ata = args.ata or settings.get("user_ata_number", "")

    result = import_myata_capture(
        Database(database_path),
        capture,
        args.season,
        expected_ata_number=expected_ata,
    )

    print(f"Capture: {result.capture_directory}")
    print(f"ATA number: {result.ata_number}")
    print(f"Member: {result.member_name}")
    print(f"Official shoot rows found: {result.detail_rows_found}")
    print(f"Official observations imported: {result.observations_imported}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
