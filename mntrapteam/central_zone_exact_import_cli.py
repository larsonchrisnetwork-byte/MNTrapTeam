from __future__ import annotations

import argparse
import re

from .central_zone_import_cli import (
    _ensure_shoot,
    _in_state,
    _stored_event_name,
    discover as central_discover,
)
from .central_zone_myata_reconcile_cli import (
    MYATA_URL,
    _detail_events,
    _group_reconciliation,
    _present_in_myata,
    _score_detail_table,
    _search_and_open,
    _open_year_detail,
    _table_rows,
)
from .connectors import SessionStore, _load_playwright
from .database import Database
from .paths import DATA


def _collect_exact_reconciliation(db: Database, season: int) -> list[dict]:
    central = central_discover(db, season)
    grouped = _group_reconciliation(central)

    if not grouped:
        return []

    store = SessionStore(DATA)
    profile = store.profile_dir("shootata")
    sync_playwright = _load_playwright()

    results = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1500, "height": 1000},
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(MYATA_URL, wait_until="domcontentloaded", timeout=60000)

        print("Complete login if needed and leave Shooter Information Center open.")
        input("Press Enter to begin exact reconciliation/write pass... ")

        if context.pages:
            page = context.pages[-1]

        entries = list(grouped.values())

        for index, entry in enumerate(entries, 1):
            candidate = entry["candidate"]
            ata = candidate.ata_number
            name = candidate.display_name
            print(f"[{index}/{len(entries)}] {name} | ATA {ata}")

            _search_and_open(page, ata, name)
            page.wait_for_timeout(900)
            _open_year_detail(page, season)
            detail = _score_detail_table(page, season)
            detail_rows = _table_rows(detail)
            myata_events = _detail_events(detail_rows)

            for source_item in entry["items"]:
                present, matched = _present_in_myata(source_item, myata_events)
                results.append(
                    {
                        "candidate": candidate,
                        "source_item": source_item,
                        "present": present,
                        "matched": matched,
                    }
                )
                row = source_item["row"]
                status = "ALREADY IN MYATA" if present else "MISSING FROM MYATA"
                print(
                    f"  {status}: {source_item['event_date']} | "
                    f"{row['club']} | E{source_item['event_id']} "
                    f"{source_item['discipline']} "
                    f"{row['hits']}/{source_item['targets']}"
                )

        context.close()

    return results


def _already_written(db: Database, shooter_id: int, club: str, event_name: str, discipline: str) -> bool:
    rows = db.query(
        """
        SELECT sc.id
        FROM scores sc
        LEFT JOIN shoots sh ON sh.id=sc.shoot_id
        WHERE sc.shooter_id=?
          AND upper(COALESCE(sh.name,''))=upper(?)
          AND upper(COALESCE(sc.event_name,''))=upper(?)
          AND lower(COALESCE(sc.discipline,''))=lower(?)
        LIMIT 1
        """,
        (
            shooter_id,
            f"2026 ATA Central Zone - {club}",
            event_name,
            discipline,
        ),
    )
    return bool(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write only exact Central Zone rows proven missing from MyATA."
    )
    parser.add_argument("action", choices=("preview", "write"), nargs="?", default="preview")
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")

    print("MNTrapTeam Central Zone Exact Missing-Row Import")
    print("================================================")
    print()

    results = _collect_exact_reconciliation(db, args.season)
    missing = [r for r in results if r["present"] is False]

    print()
    print(f"Rows proven missing from MyATA: {len(missing)}")

    for r in missing:
        item = r["source_item"]
        row = item["row"]
        print(
            f"{r['candidate'].ata_number} | {r['candidate'].display_name} | "
            f"{item['event_date']} | {row['club']} | "
            f"E{item['event_id']} {item['discipline']} "
            f"{row['hits']}/{item['targets']}"
        )

    if args.action == "preview":
        print()
        print("PREVIEW ONLY — no database changes made.")
        return 0

    written = 0
    skipped_existing = 0

    for r in missing:
        candidate = r["candidate"]
        item = r["source_item"]
        row = item["row"]
        event_name = _stored_event_name(item["event_id"])

        if _already_written(
            db,
            candidate.shooter_id,
            row["club"],
            event_name,
            item["discipline"],
        ):
            skipped_existing += 1
            continue

        shoot_id = _ensure_shoot(db, row["club"])
        db.execute(
            """
            INSERT INTO scores(
                shooter_id,shoot_id,event_date,event_name,discipline,
                targets,hits,in_state,club_key,source,official,raw_name
            ) VALUES(?,?,?,?,?,?,?,?,?,?,0,?)
            """,
            (
                candidate.shooter_id,
                shoot_id,
                item["event_date"],
                event_name,
                item["discipline"],
                item["targets"],
                row["hits"],
                _in_state(row["club"]),
                row["club"],
                "ATA Central Zone exact-reconcile",
                row["name"],
            ),
        )
        written += 1

    print()
    print(f"Exact missing Central Zone rows written: {written}")
    print(f"Already-present provisional rows skipped: {skipped_existing}")
    print("Official MyATA season_stats were NOT modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
