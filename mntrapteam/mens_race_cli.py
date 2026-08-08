from __future__ import annotations

from .database import Database
from .live_dashboard import live_team_rows
from .paths import DATA
from .rules import RulesEngine
from .services import TeamService


def main() -> int:
    db = Database(DATA / "mntrapteam.db")
    service = TeamService(db, RulesEngine())
    result = live_team_rows(db, service, 2026, "MEN")

    print("MNTrapTeam 2026 Men's Team Race — Official vs Current")
    print("=====================================================")
    summary = result["summary"]
    print(
        f"Tracked={summary['tracked']} | "
        f"HAA={summary['haa_qualified']} | "
        f"Fully qualified={summary['fully_qualified']} | "
        f"Current team={summary['selected']}/{summary['team_size']} | "
        f"Pending targets={summary['pending_targets']}"
    )
    print()

    for row in result["rows"]:
        team = "*" if row.get("live_team") else " "
        pending = int(row.get("pending_targets") or 0)
        print(
            f"{int(row['race_rank']):>3} {team} "
            f"{row.get('display_name',''):<28} "
            f"Current {float(row.get('current_hoa') or 0):6.2f} | "
            f"MyATA {float(row.get('official_hoa') or 0):6.2f} | "
            f"Pending {pending:4d} | "
            f"{row.get('qualification_status')} | "
            f"{row.get('need_to_qualify')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
