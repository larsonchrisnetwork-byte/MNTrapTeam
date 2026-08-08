from __future__ import annotations

from collections import defaultdict

from .database import Database
from .identity import normalize_ata
from .paths import DATA


ZONE_EVENT_MAP = {
    "N ZONE CHAMPIONSHIP SINGLES": ("singles", 200),
    "N ZONE CHAMPIONSHIP HANDICAP": ("handicap", 100),
    "N ZONE CHAMPIONSHIP DOUBLES": ("doubles", 100),
}


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    rows = [
        dict(r)
        for r in db.query(
            """
            SELECT
                s.id AS shooter_id,
                s.ata_number,
                s.display_name,
                sc.event_name,
                sc.discipline,
                sc.targets,
                sc.hits,
                sc.source
            FROM scores sc
            JOIN shooters s ON s.id=sc.shooter_id
            WHERE upper(COALESCE(sc.event_name,'')) IN (
                'N ZONE CHAMPIONSHIP SINGLES',
                'N ZONE CHAMPIONSHIP HANDICAP',
                'N ZONE CHAMPIONSHIP DOUBLES'
            )
            ORDER BY s.display_name, sc.event_name
            """
        )
    ]

    grouped = defaultdict(lambda: {
        "name": "",
        "ata": "",
        "singles": 0,
        "handicap": 0,
        "doubles": 0,
        "scores": [],
    })

    for row in rows:
        ata = normalize_ata(row.get("ata_number"))
        if not ata:
            continue

        item = grouped[ata]
        item["name"] = str(row.get("display_name") or "").strip()
        item["ata"] = ata

        event = str(row.get("event_name") or "").upper().strip()
        discipline, required = ZONE_EVENT_MAP[event]

        targets = int(row.get("targets") or 0)
        item[discipline] += targets
        item["scores"].append(row)

    completers = []
    partials = []

    for ata, item in grouped.items():
        complete = (
            item["singles"] >= 200
            and item["handicap"] >= 100
            and item["doubles"] >= 100
        )

        if complete:
            completers.append(item)
        else:
            partials.append(item)

    completers.sort(key=lambda x: x["name"].upper())
    partials.sort(key=lambda x: x["name"].upper())

    print("MNTrapTeam Northern Zone HAA Candidate Report")
    print("=============================================")
    print(f"Shooters with Northern Zone championship data: {len(grouped)}")
    print(f"Complete 200S/100H/100D candidates: {len(completers)}")
    print(f"Partial/incomplete candidates: {len(partials)}")
    print()

    print("COMPLETE NORTHERN ZONE HAA CANDIDATES")
    print("-------------------------------------")
    for item in completers:
        print(
            f"{item['ata']} | {item['name']} | "
            f"S {item['singles']} | "
            f"H {item['handicap']} | "
            f"D {item['doubles']}"
        )

    if partials:
        print()
        print("PARTIAL NORTHERN ZONE RECORDS")
        print("-----------------------------")
        for item in partials:
            missing = []
            if item["singles"] < 200:
                missing.append(f"S {item['singles']}/200")
            if item["handicap"] < 100:
                missing.append(f"H {item['handicap']}/100")
            if item["doubles"] < 100:
                missing.append(f"D {item['doubles']}/100")

            print(
                f"{item['ata']} | {item['name']} | "
                + ", ".join(missing)
            )

    print()
    print(
        "NOTE: This report identifies only event-complete candidates. "
        "It does NOT yet verify that the shooter resides in the Northern Zone."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
