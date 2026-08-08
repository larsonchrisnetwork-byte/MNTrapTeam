from __future__ import annotations

import argparse
from collections import Counter

from .database import Database
from .paths import DATA
from .state_team_lock import build_locks, write_locks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preview", "write"), nargs="?", default="preview")
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")
    locks = write_locks(db, args.season) if args.action == "write" else build_locks(db, args.season)

    print(f"MNTrapTeam {args.season} HAA Candidate / Team Category Lock")
    print("======================================================")
    print("HAA is the hard gate, and the qualifying HAA category locks the State Team pool.")
    print()

    team_counts = Counter(item["state_team"] for item in locks)
    print("TEAM POOL COUNTS")
    print("----------------")
    for team, count in sorted(team_counts.items()):
        print(f"{team}: {count}")

    men = [item for item in locks if item["state_team"] == "MEN"]
    print()
    print("MEN'S OPEN FROZEN HAA POOL")
    print("--------------------------")
    for item in men:
        print(
            f"{item['ata_number']} | {item['display_name']} | "
            f"{item['haa_route']} | {item['qualifying_category']} | "
            f"{item['qualifying_event']}"
        )

    print()
    print(f"Men's HAA-qualified candidate pool: {len(men)}")
    print(f"All HAA-qualified State Team candidates: {len(locks)}")

    if args.action == "preview":
        print("PREVIEW ONLY — no database changes made.")
    else:
        print("LOCK WRITTEN — season HAA/category flags now reflect the frozen pool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
