from __future__ import annotations

import argparse

from .database import Database
from .paths import DATA
from .shootscoreboard_web import import_public_shoot, load_public_shoot


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import a public ShootScoreBoard shoot into MNTrapTeam"
    )
    parser.add_argument("shoot", help="Shoot ID or ShootScoreBoard URL")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--club", default="")
    parser.add_argument("--all-states", action="store_true")
    args = parser.parse_args()

    print("Downloading public ShootScoreBoard reports...")
    shoot = load_public_shoot(args.shoot)
    print(
        f"Found {shoot.name}: {len(shoot.events)} events, "
        f"{sum(len(event.entries) for event in shoot.events)} score rows."
    )
    result = import_public_shoot(
        Database(DATA / "mntrapteam.db"),
        shoot,
        args.season,
        mn_only=not args.all_states,
        club=args.club,
    )
    print(f"Imported score rows: {result.score_rows_imported}")
    print(f"New shooter records: {result.shooters_created}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    print(
        "ShootScoreBoard data is unofficial and should be reconciled "
        "with authorized ShootATA totals."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
