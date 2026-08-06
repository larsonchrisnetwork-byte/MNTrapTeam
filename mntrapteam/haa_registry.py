from __future__ import annotations

import argparse
from pathlib import Path

from .database import Database
from .haa_gate import (
    active_team_pool,
    import_registry_csv,
    rebuild_season_haa_flags,
)
from .paths import DATA
from .rules import RuleEngine
from .services import TeamService


def db_path() -> Path:
    return DATA / "mntrapteam.db"


def main() -> int:
    parser = argparse.ArgumentParser(description="MNTrapTeam qualifying HAA registry")
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="Import a reviewed HAA registry CSV")
    imp.add_argument("csv")
    imp.add_argument("--season", type=int, default=2026)

    rebuild = sub.add_parser("rebuild", help="Rebuild season HAA flags")
    rebuild.add_argument("--season", type=int, default=2026)

    args = parser.parse_args()
    database = Database(db_path())

    if args.command == "import":
        result = import_registry_csv(database, Path(args.csv), args.season)
        print(f"Rows read: {result['rows_read']}")
        print(f"Rows imported: {result['rows_imported']}")
        print(f"Shooters created: {result['shooters_created']}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        return 0

    count = rebuild_season_haa_flags(database, args.season)
    print(f"Rebuilt HAA status for {count} season-stat rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
