from __future__ import annotations

import argparse
import json
from pathlib import Path

from .database import Database
from .myata import capture_myata
from .paths import CONFIG, DATA


def settings() -> dict:
    return json.loads((CONFIG / "settings.json").read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture and import official MyATA target-year totals"
    )
    parser.add_argument("--season", type=int)
    parser.add_argument("--ata")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    config = settings()
    season = args.season or int(config.get("season", 2026))
    ata = args.ata or config.get("user_ata_number", "")
    database_path = Path(config.get("database", "data/mntrapteam.db"))
    if not database_path.is_absolute():
        database_path = CONFIG.parent / database_path

    result = capture_myata(
        DATA,
        season=season,
        ata_number=ata,
        database=Database(database_path),
        headed=args.headed,
    )

    print(f"Page: {result.page_title}")
    print(f"URL: {result.page_url}")
    print(f"Tables captured: {result.tables}")
    print(f"JSON responses captured: {result.json_responses}")
    print(f"Official totals recognized: {result.totals_found}")
    print(f"Official totals imported: {result.imported}")
    print(f"Capture directory: {result.directory}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")

    return 0 if result.imported or result.tables else 1


if __name__ == "__main__":
    raise SystemExit(main())
