from __future__ import annotations

import csv

from .database import Database
from .haa_gate import haa_status
from .official_baseline import ensure_schema, get_baseline
from .paths import DATA
from .rules import RulesEngine
from .services import TeamService


OUTPUT = DATA / "connector_downloads" / "mens_haa_baseline_refresh.csv"


def main() -> int:
    db = Database(DATA / "mntrapteam.db")
    rules = RulesEngine()
    service = TeamService(db, rules)
    ensure_schema(db)

    rows = service.rankings(2026, "MEN")
    targets = []
    already_ready = 0

    for row in rows:
        shooter_id = int(row["id"])
        haa = haa_status(db, 2026, shooter_id)
        haa_qualified = bool(haa.get("haa_qualified")) or bool(row.get("haa_complete"))
        if not haa_qualified:
            continue

        baseline = get_baseline(db, shooter_id, 2026)
        through = str(baseline.get("official_through_date") or "")
        if through:
            already_ready += 1
            continue

        ata = "".join(ch for ch in str(row.get("ata_number") or "") if ch.isdigit())
        if not ata:
            continue

        targets.append(
            {
                "ata_number": ata,
                "display_name": row.get("display_name") or "",
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ata_number", "display_name"])
        writer.writeheader()
        writer.writerows(targets)

    print("MNTrapTeam Men's HAA Baseline Refresh List")
    print("==========================================")
    print(f"HAA-qualified Men's shooters already baseline-ready: {already_ready}")
    print(f"HAA-qualified Men's shooters needing MyATA-through date: {len(targets)}")
    print(f"Target file: {OUTPUT}")
    print()

    for item in targets:
        print(f"{item['ata_number']} | {item['display_name']}")

    if targets:
        print()
        print("Run:")
        print('& ".\\.venv\\Scripts\\python.exe" -m mntrapteam.myata_bulk_dom_cli `')
        print("  --season 2026 `")
        print(f'  --ata-file "{OUTPUT}" `')
        print("  --manual-assist `")
        print("  --refresh")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
