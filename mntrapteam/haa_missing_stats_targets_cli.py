from __future__ import annotations

from .database import Database
from .paths import DATA
from .myata_bulk_dom_cli import main as bulk_main


TARGET_ATAS = ("2216215", "2306892")


def _rows(db, sql, params=()):
    return [dict(r) for r in db.query(sql, params)]


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    print("MNTrapTeam HAA Missing-Stats Target List")
    print("=======================================")
    print()

    targets = []

    for ata in TARGET_ATAS:
        rows = _rows(
            db,
            """
            SELECT id, ata_number, display_name, state
            FROM shooters
            WHERE ata_number=?
            """,
            (ata,),
        )

        if len(rows) != 1:
            print(f"{ata} | ERROR: expected one shooter row, found {len(rows)}")
            continue

        shooter = rows[0]

        stats = _rows(
            db,
            """
            SELECT id, season, source
            FROM season_stats
            WHERE shooter_id=? AND season=2026
            """,
            (shooter["id"],),
        )

        status = "HAS STATS" if stats else "MISSING STATS"
        print(
            f"{ata} | {shooter['display_name']} | "
            f"id={shooter['id']} | {status}"
        )

        if not stats:
            targets.append(shooter)

    print()
    print(f"Missing-stat targets: {len(targets)}")

    if not targets:
        print("Nothing to repair.")
        return 0

    print()
    print("Run the existing MyATA bulk importer for exactly these ATA numbers:")
    for shooter in targets:
        print(f"  {shooter['ata_number']} | {shooter['display_name']}")

    print()
    print(
        "This helper is intentionally read-only. "
        "Use the generated CSV target file with the targeted importer command below."
    )

    target_csv = DATA / "connector_downloads" / "myata_targeted_haa_missing_stats.csv"
    target_csv.parent.mkdir(parents=True, exist_ok=True)

    lines = ["ata_number,display_name"]
    for shooter in targets:
        safe_name = str(shooter["display_name"]).replace('"', '""')
        lines.append(f'{shooter["ata_number"]},"{safe_name}"')

    target_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Target file: {target_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
