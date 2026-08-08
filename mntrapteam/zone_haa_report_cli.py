from __future__ import annotations

from .database import Database
from .paths import DATA


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    rows = [
        dict(r)
        for r in db.query(
            """
            SELECT
                s.ata_number,
                s.display_name,
                z.zone,
                z.residence_city,
                z.singles_targets,
                z.handicap_targets,
                z.doubles_targets,
                z.verified
            FROM zone_haa_qualifications z
            JOIN shooters s ON s.id=z.shooter_id
            WHERE z.season=2026
            ORDER BY z.zone, s.display_name
            """
        )
    ]

    print("MNTrapTeam 2026 Zone HAA Qualifications")
    print("=======================================")

    if not rows:
        print("No Zone HAA records.")
        return 0

    for row in rows:
        print(
            f"{row['ata_number']} | {row['display_name']} | "
            f"{row['zone']} | {row['residence_city']} | "
            f"S {row['singles_targets']} "
            f"H {row['handicap_targets']} "
            f"D {row['doubles_targets']} | "
            f"{'VERIFIED' if row['verified'] else 'NOT VERIFIED'}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
