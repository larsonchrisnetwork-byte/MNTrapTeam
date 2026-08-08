from __future__ import annotations

import csv
from pathlib import Path

from .database import Database
from .paths import DATA


TARGET_FILE = DATA / "connector_downloads" / "myata_targeted_haa_missing_stats.csv"


def main() -> int:
    if not TARGET_FILE.exists():
        raise SystemExit(
            "Target file not found. Run "
            "`python -m mntrapteam.haa_missing_stats_targets_cli` first."
        )

    rows = list(csv.DictReader(TARGET_FILE.read_text(encoding="utf-8").splitlines()))

    print("MNTrapTeam Targeted MyATA Missing-Stats Import")
    print("=============================================")
    print()
    print("This command prepares the exact two-shooter batch.")
    print()

    for i, row in enumerate(rows, 1):
        print(
            f"[{i}/{len(rows)}] {row.get('display_name')} | "
            f"ATA {row.get('ata_number')}"
        )

    print()
    print(
        "Use the existing bulk MyATA importer with --manual-assist and "
        "--limit 2 after temporarily placing these two shooters first in the batch."
    )
    print(
        "Because the current bulk importer does not yet accept an explicit ATA-list file, "
        "the next patch will add --ata-file support instead of relying on sort order."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
