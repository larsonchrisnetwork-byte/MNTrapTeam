from __future__ import annotations

from collections import defaultdict

from .database import Database
from .identity import normalize_ata, normalize_person_name
from .paths import DATA


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    rows = db.query(
        """
        SELECT
            id,
            ata_number,
            display_name
        FROM shooters
        ORDER BY display_name, ata_number
        """
    )

    by_ata = defaultdict(list)
    by_name = defaultdict(list)

    for row in rows:
        item = dict(row)
        ata = normalize_ata(item.get("ata_number"))
        name = str(item.get("display_name") or "").strip()

        if ata:
            by_ata[ata].append(item)

        normalized_name = normalize_person_name(name)
        if normalized_name:
            by_name[normalized_name].append(item)

    duplicate_ata = {
        ata: items
        for ata, items in by_ata.items()
        if len(items) > 1
    }

    duplicate_names = {
        name: items
        for name, items in by_name.items()
        if len({normalize_ata(i.get("ata_number")) for i in items}) > 1
    }

    print("MNTrapTeam Shooter Identity Audit")
    print("================================")
    print(f"Shooter records: {len(rows)}")
    print(f"Duplicate ATA numbers: {len(duplicate_ata)}")
    print(f"Same-name / different-ATA groups: {len(duplicate_names)}")
    print()

    if duplicate_ata:
        print("CRITICAL: DUPLICATE ATA NUMBERS")
        print("-------------------------------")
        for ata, items in sorted(duplicate_ata.items()):
            print(f"ATA {ata}")
            for item in items:
                print(
                    f"  id={item.get('id')} | "
                    f"{item.get('display_name')}"
                )
        print()
    else:
        print("No duplicate ATA-number records found.")
        print()

    if duplicate_names:
        print("SAME NAME, DIFFERENT ATA — KEEP SEPARATE")
        print("----------------------------------------")
        for normalized_name, items in sorted(duplicate_names.items()):
            print(normalized_name)
            for item in items:
                print(
                    f"  ATA {normalize_ata(item.get('ata_number'))} | "
                    f"id={item.get('id')} | "
                    f"{item.get('display_name')}"
                )
        print()
    else:
        print("No same-name/different-ATA groups found.")
        print()

    print("Identity policy:")
    print("  ATA number = authoritative primary identity")
    print("  Name = display/search aid only")
    print("  Never merge two records solely because names match")

    return 2 if duplicate_ata else 0


if __name__ == "__main__":
    raise SystemExit(main())
