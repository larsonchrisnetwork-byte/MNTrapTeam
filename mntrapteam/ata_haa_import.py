from __future__ import annotations

import argparse
from pathlib import Path

from .ata_haa_pdf import import_ata_haa_pdf, import_ata_haa_url
from .database import Database
from .paths import DATA


def database_path() -> Path:
    return DATA / "mntrapteam.db"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import ATA-number-bearing HAA results into MNTrapTeam"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--pdf")

    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--route", choices=["STATE", "ZONE"], required=True)
    parser.add_argument("--zone", choices=["CENTRAL", "NORTHERN", "SOUTHERN"])
    parser.add_argument("--shoot-name", required=True)
    parser.add_argument("--shoot-date", required=True)
    parser.add_argument(
        "--coverage",
        choices=["PARTIAL", "COMPLETE"],
        default="PARTIAL",
    )
    parser.add_argument("--source-label", default="")
    parser.add_argument("--all-states", action="store_true")
    args = parser.parse_args()

    database = Database(database_path())
    common = dict(
        season=args.season,
        route=args.route,
        shoot_name=args.shoot_name,
        shoot_date=args.shoot_date,
        shoot_zone=args.zone or "",
        source_label=args.source_label,
        source_coverage=args.coverage,
        minnesota_only=not args.all_states,
    )

    if args.url:
        result = import_ata_haa_url(database, args.url, **common)
    else:
        result = import_ata_haa_pdf(database, Path(args.pdf), **common)

    print(f"ATA-bearing rows found: {result.rows_found}")
    print(f"Minnesota rows considered: {result.minnesota_rows}")
    print(f"HAA records imported: {result.rows_imported}")
    print(f"Shooters created: {result.shooters_created}")
    print(f"Shooters updated by ATA number: {result.shooters_updated}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
