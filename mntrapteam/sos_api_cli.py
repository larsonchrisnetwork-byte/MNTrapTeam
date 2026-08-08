from __future__ import annotations

import argparse
import getpass
from datetime import date

from .database import Database
from .paths import DATA
from .sos_api import (
    SOSClient,
    candidate_for_shoot_id,
    discover_minnesota_shoots,
    import_sos_shoot,
)


def _login() -> SOSClient:
    print("SOS Clays sign-in (credentials are not saved by MNTrapTeam)")
    email = input("SOS email: ").strip()
    password = getpass.getpass("SOS password: ")
    client = SOSClient()
    client.login(email, password)
    print("SOS login successful.")
    return client


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authenticated SOS Clays live-score importer"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_mn = sub.add_parser("list-mn", help="List MN shoots in a target year")
    list_mn.add_argument("--season", type=int, default=2026)

    one = sub.add_parser("import-shoot", help="Import one SOS shoot")
    one.add_argument("shoot_id", type=int)
    one.add_argument("--season", type=int, default=2026)
    one.add_argument("--all-states", action="store_true")

    sync = sub.add_parser("sync-mn", help="Import all MN shoots in a target year")
    sync.add_argument("--season", type=int, default=2026)

    args = parser.parse_args()
    client = _login()

    if args.command == "list-mn":
        shoots = discover_minnesota_shoots(client, args.season)
        print(f"Minnesota SOS shoots in target year {args.season}: {len(shoots)}")
        for shoot in shoots:
            clubs = ", ".join(location.club_name for location in shoot.locations)
            print(f"{shoot.shoot_id} | {shoot.start_date} | {shoot.name} | {clubs}")
        return 0

    database = Database(DATA / "mntrapteam.db")

    if args.command == "import-shoot":
        candidate = candidate_for_shoot_id(client, args.shoot_id)
        result = import_sos_shoot(
            database,
            client,
            candidate,
            args.season,
            mn_only=not args.all_states,
        )
        _print_result(result)
        return 0

    all_shoots = discover_minnesota_shoots(client, args.season)
    today = date.today().isoformat()
    shoots = [shoot for shoot in all_shoots if shoot.start_date <= today]
    future_shoots = [shoot for shoot in all_shoots if shoot.start_date > today]

    total_rows = 0
    print(f"Importing {len(shoots)} Minnesota SOS shoots...")
    for shoot in future_shoots:
        print(
            f"Skipping future shoot: {shoot.shoot_id} | "
            f"{shoot.start_date} | {shoot.name}"
        )
    for index, shoot in enumerate(shoots, 1):
        print(f"[{index}/{len(shoots)}] {shoot.start_date} {shoot.name}")
        result = import_sos_shoot(database, client, shoot, args.season, mn_only=True)
        total_rows += result.score_rows_imported
        print(f"  {result.score_rows_imported} MN score rows")
        for warning in result.warnings[:5]:
            print(f"  WARNING: {warning}")
    print(f"SOS sync complete: {total_rows} MN score rows written/updated.")
    return 0


def _print_result(result) -> None:
    print(f"Shoot: {result.shoot_name} ({result.shoot_id})")
    print(f"Events: {result.events_found}")
    print(f"High-gun rows found: {result.score_rows_found}")
    print(f"MN score rows written/updated: {result.score_rows_imported}")
    print(f"New shooters: {result.shooters_created}")
    print(f"Reconciliation observations: {result.observations_written}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    raise SystemExit(main())
