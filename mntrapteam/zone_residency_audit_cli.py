from __future__ import annotations

from .database import Database
from .identity import normalize_ata
from .paths import DATA


CANDIDATE_ATAS = ("1776550", "0416492", "2805615")


def _rows(db, sql, params=()):
    return [dict(r) for r in db.query(sql, params)]


def _table_names(db):
    return [
        r["name"]
        for r in _rows(
            db,
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
    ]


def _columns(db, table):
    safe = table.replace('"', '""')
    return _rows(db, f'PRAGMA table_info("{safe}")')


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    shooters = _rows(
        db,
        """
        SELECT *
        FROM shooters
        WHERE ata_number IN (?,?,?)
        ORDER BY display_name
        """,
        CANDIDATE_ATAS,
    )

    print("MNTrapTeam Northern Zone Residency Data Audit")
    print("=============================================")
    print()

    print("SHOOTER RECORDS")
    print("---------------")
    for shooter in shooters:
        print(
            f"ATA {normalize_ata(shooter.get('ata_number'))} | "
            f"{shooter.get('display_name')}"
        )
        for key, value in shooter.items():
            if value not in (None, "", 0):
                print(f"  {key}: {value}")
        print()

    # Find database columns that might contain residence/location data.
    location_words = (
        "city",
        "county",
        "state",
        "province",
        "address",
        "zip",
        "postal",
        "town",
        "residence",
        "location",
    )

    candidate_ids = {
        int(s["id"]): normalize_ata(s.get("ata_number"))
        for s in shooters
        if s.get("id") is not None
    }

    print("OTHER TABLES WITH POSSIBLE RESIDENCY FIELDS")
    print("-------------------------------------------")

    found_any = False

    for table in _table_names(db):
        columns = _columns(db, table)
        col_names = [c["name"] for c in columns]

        location_cols = [
            c for c in col_names
            if any(word in c.lower() for word in location_words)
        ]

        if not location_cols:
            continue

        shooter_fk = next(
            (
                c for c in col_names
                if c.lower() in {
                    "shooter_id",
                    "member_id",
                    "shooterid",
                }
            ),
            None,
        )

        ata_col = next(
            (
                c for c in col_names
                if c.lower() in {
                    "ata_number",
                    "atanumber",
                    "ata_id",
                    "ataid",
                }
            ),
            None,
        )

        if not shooter_fk and not ata_col:
            continue

        safe_table = table.replace('"', '""')

        rows = []

        if shooter_fk and candidate_ids:
            placeholders = ",".join("?" for _ in candidate_ids)
            rows.extend(
                _rows(
                    db,
                    f'SELECT * FROM "{safe_table}" '
                    f'WHERE "{shooter_fk}" IN ({placeholders})',
                    tuple(candidate_ids.keys()),
                )
            )

        if ata_col:
            placeholders = ",".join("?" for _ in CANDIDATE_ATAS)
            rows.extend(
                _rows(
                    db,
                    f'SELECT * FROM "{safe_table}" '
                    f'WHERE "{ata_col}" IN ({placeholders})',
                    CANDIDATE_ATAS,
                )
            )

        # Deduplicate printed rows by repr so dual lookup doesn't repeat.
        seen = set()
        unique_rows = []
        for row in rows:
            marker = repr(sorted(row.items()))
            if marker not in seen:
                seen.add(marker)
                unique_rows.append(row)

        if not unique_rows:
            continue

        found_any = True
        print(f"{table} | possible location fields: {', '.join(location_cols)}")

        for row in unique_rows:
            identity_bits = []
            if shooter_fk:
                identity_bits.append(f"{shooter_fk}={row.get(shooter_fk)}")
            if ata_col:
                identity_bits.append(f"{ata_col}={row.get(ata_col)}")

            print("  " + " | ".join(identity_bits))

            for col in location_cols:
                value = row.get(col)
                if value not in (None, ""):
                    print(f"    {col}: {value}")

        print()

    if not found_any:
        print("No linked city/county/address fields found for these candidates.")
        print()

    print("Next rule:")
    print(
        "  Zone HAA is accepted only after residence maps to the same "
        "MTA zone as the Zone Shoot."
    )
    print(
        "  No shooter will be assigned a zone solely from club location, "
        "shoot location, or name."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
