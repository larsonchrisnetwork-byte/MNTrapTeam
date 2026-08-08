from __future__ import annotations

from collections import defaultdict

from .database import Database
from .identity import normalize_ata, normalize_person_name
from .paths import DATA


def _tables(db):
    return [
        dict(r)["name"]
        for r in db.query(
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
    return [
        dict(r)["name"]
        for r in db.query(f'PRAGMA table_info("{safe}")')
    ]


def _count_refs(db, table, column, shooter_id):
    safe_table = table.replace('"', '""')
    safe_col = column.replace('"', '""')
    rows = db.query(
        f'SELECT COUNT(*) AS n FROM "{safe_table}" '
        f'WHERE "{safe_col}"=?',
        (shooter_id,),
    )
    return int(dict(rows[0])["n"]) if rows else 0


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    shooters = [
        dict(r)
        for r in db.query(
            "SELECT id, ata_number, display_name FROM shooters ORDER BY id"
        )
    ]

    by_name = defaultdict(list)
    for shooter in shooters:
        key = normalize_person_name(shooter.get("display_name"))
        if key:
            by_name[key].append(shooter)

    groups = []
    for key, items in by_name.items():
        blank = [
            item for item in items
            if not normalize_ata(item.get("ata_number"))
        ]
        numbered = [
            item for item in items
            if normalize_ata(item.get("ata_number"))
        ]
        if blank and numbered:
            groups.append((key, blank, numbered))

    table_columns = {}
    for table in _tables(db):
        if table == "shooters":
            continue
        cols = _columns(db, table)
        # Check common shooter FK names conservatively.
        shooter_cols = [
            col for col in cols
            if col.lower() in {
                "shooter_id",
                "member_id",
                "shooterid",
            }
        ]
        if shooter_cols:
            table_columns[table] = shooter_cols

    print("MNTrapTeam Blank-ATA Reference Audit")
    print("===================================")
    print(f"Candidate same-name groups: {len(groups)}")
    print()

    referenced_blank_rows = 0

    for name, blanks, numbered in groups:
        print(name)

        for target in numbered:
            print(
                f"  NUMBERED id={target['id']} | "
                f"ATA {normalize_ata(target.get('ata_number'))} | "
                f"{target.get('display_name')}"
            )

        for blank in blanks:
            total_refs = 0
            ref_lines = []

            for table, columns in table_columns.items():
                for column in columns:
                    n = _count_refs(
                        db,
                        table,
                        column,
                        int(blank["id"]),
                    )
                    if n:
                        total_refs += n
                        ref_lines.append(
                            f"{table}.{column}={n}"
                        )

            print(
                f"  BLANK    id={blank['id']} | "
                f"{blank.get('display_name')} | "
                f"references={total_refs}"
            )

            for line in ref_lines:
                print(f"      {line}")

            if total_refs:
                referenced_blank_rows += 1

        print()

    print(
        "Blank-ATA rows with references:",
        referenced_blank_rows,
    )

    if referenced_blank_rows == 0:
        print(
            "SAFE CANDIDATES: all listed blank-ATA rows are unreferenced "
            "and can be deleted without moving shooter-linked data."
        )
    else:
        print(
            "DO NOT DELETE YET: at least one blank-ATA row still owns data. "
            "Those references must be reviewed/migrated by ATA-number identity."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
