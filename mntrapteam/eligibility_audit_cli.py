from __future__ import annotations

from .database import Database
from .eligibility_engine import evaluate_mens_open
from .paths import DATA


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    shooters = [
        dict(r)
        for r in db.query(
            """
            SELECT id, ata_number, display_name
            FROM shooters
            WHERE state='MN' OR state IS NULL
            ORDER BY display_name
            """
        )
    ]

    print("MNTrapTeam v4 Men's Open Eligibility Audit")
    print("==========================================")
    print()

    eligible = 0
    ineligible = 0

    for shooter in shooters:
        result = evaluate_mens_open(db, int(shooter["id"]), 2026)

        if result.eligible:
            eligible += 1
            status = "ELIGIBLE"
        else:
            ineligible += 1
            status = "NOT ELIGIBLE"

        print(
            f"{shooter.get('ata_number') or ''} | "
            f"{shooter.get('display_name')} | {status} | "
            f"HAA={result.haa_source} | "
            f"S {result.values['total_singles']} "
            f"H {result.values['total_handicap']} "
            f"D {result.values['total_doubles']} | "
            f"MN S {result.values['mn_singles']} "
            f"H {result.values['mn_handicap']} "
            f"D {result.values['mn_doubles']} | "
            f"Clubs {result.values['mn_clubs']}"
        )

        if result.reasons:
            for reason in result.reasons:
                print(f"    - {reason}")

    print()
    print(f"Eligible: {eligible}")
    print(f"Not eligible: {ineligible}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
