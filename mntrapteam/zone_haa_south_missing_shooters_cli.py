from __future__ import annotations

from .database import Database
from .paths import DATA


MISSING = (
    {
        "ata_number": "2216215",
        "first_name": "Anna",
        "last_name": "Berger",
        "display_name": "Anna M Berger",
        "state": "MN",
        "category": "",
    },
    {
        "ata_number": "2306892",
        "first_name": "Tucker",
        "last_name": "Fredrickson",
        "display_name": "Tucker L Fredrickson",
        "state": "MN",
        "category": "",
    },
)


def _rows(db, sql, params=()):
    return [dict(r) for r in db.query(sql, params)]


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    print("MNTrapTeam Missing Southern Shooter Repair")
    print("=========================================")
    print()

    created = 0
    existing = 0

    for item in MISSING:
        ata = item["ata_number"]

        rows = _rows(
            db,
            """
            SELECT id, ata_number, display_name
            FROM shooters
            WHERE ata_number=?
            """,
            (ata,),
        )

        if len(rows) == 1:
            print(
                f"{ata} | {rows[0]['display_name']} | already exists"
            )
            existing += 1
            continue

        if len(rows) > 1:
            raise RuntimeError(
                f"Refusing repair: ATA {ata} has {len(rows)} shooter rows"
            )

        db.execute(
            """
            INSERT INTO shooters(
                ata_number,
                first_name,
                last_name,
                display_name,
                state,
                category,
                active,
                created_at,
                updated_at
            )
            VALUES(?,?,?,?,?,?,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            """,
            (
                item["ata_number"],
                item["first_name"],
                item["last_name"],
                item["display_name"],
                item["state"],
                item["category"],
            ),
        )

        check = _rows(
            db,
            """
            SELECT id, ata_number, display_name
            FROM shooters
            WHERE ata_number=?
            """,
            (ata,),
        )

        if len(check) != 1:
            raise RuntimeError(
                f"Repair verification failed for ATA {ata}"
            )

        print(
            f"{ata} | {check[0]['display_name']} | CREATED id={check[0]['id']}"
        )
        created += 1

    print()
    print(f"Created: {created}")
    print(f"Already existed: {existing}")
    print()
    print(
        "Next: rerun the Southern verified write. Existing qualifiers "
        "will upsert safely; these two should no longer be skipped."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
