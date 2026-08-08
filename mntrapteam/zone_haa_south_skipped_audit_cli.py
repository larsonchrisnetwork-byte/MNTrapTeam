from __future__ import annotations

from .database import Database
from .identity import normalize_ata
from .paths import DATA


TARGETS = (
    ("2216215", "Anna M Berger", "LE SUEUR"),
    ("2306892", "Tucker L Fredrickson", "LE SUEUR"),
)


def _rows(db, sql, params=()):
    return [dict(r) for r in db.query(sql, params)]


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    print("MNTrapTeam Southern Skipped-Shooter Audit")
    print("=========================================")
    print()

    for ata, expected_name, city in TARGETS:
        print(f"ATA {ata} | {expected_name}")

        exact = _rows(
            db,
            """
            SELECT id, ata_number, display_name, first_name, last_name, state, category
            FROM shooters
            WHERE ata_number=?
            """,
            (ata,),
        )

        print(f"  exact ATA rows: {len(exact)}")
        for row in exact:
            print(f"    {row}")

        surname = expected_name.split()[-1]

        similar = _rows(
            db,
            """
            SELECT id, ata_number, display_name, first_name, last_name, state, category
            FROM shooters
            WHERE upper(COALESCE(display_name,'')) LIKE ?
               OR upper(COALESCE(last_name,''))=?
            ORDER BY id
            """,
            (f"%{surname.upper()}%", surname.upper()),
        )

        print(f"  surname/name-like rows: {len(similar)}")
        for row in similar:
            print(f"    {row}")

        print()

    print("No database changes were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
