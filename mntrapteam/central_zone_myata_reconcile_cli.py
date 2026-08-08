from __future__ import annotations

import argparse
import re

from .central_zone_import_cli import discover as central_discover
from .connectors import SessionStore, _load_playwright
from .database import Database
from .myata_bulk_dom_cli import (
    MYATA_URL,
    _search_and_open,
    _open_year_detail,
    _score_detail_table,
    _table_rows,
)
from .paths import DATA


def _int(value) -> int:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _normalize_date(value: str) -> str:
    text = str(value or "").strip()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", text)
    if not m:
        return text
    month, day, year = map(int, m.groups())
    if year < 100:
        year += 2000
    return f"{year:04d}-{month:02d}-{day:02d}"


def _detail_events(rows: list[list[str]]) -> list[dict]:
    """
    Convert MyATA Score Details rows into one event record per discipline.

    Observed columns:
    #, Date, Club,
    Singles Shot, Singles Hit, Singles League Shot, Singles League Hit,
    Handicap Yds, Prev, Handicap Shot, Handicap Hit, Earn,
    Doubles Shot, Doubles Hit, Doubles League Shot, Doubles League Hit.
    """
    events = []

    for cells in rows:
        if len(cells) < 14:
            continue

        if not re.search(r"\d", str(cells[1] if len(cells) > 1 else "")):
            continue

        date = _normalize_date(cells[1])
        club = str(cells[2] or "").strip()

        s_shot = _int(cells[3])
        s_hit = _int(cells[4])
        if s_shot:
            events.append(
                {
                    "date": date,
                    "club": club,
                    "discipline": "singles",
                    "targets": s_shot,
                    "hits": s_hit,
                }
            )

        h_shot = _int(cells[9])
        h_hit = _int(cells[10])
        if h_shot:
            events.append(
                {
                    "date": date,
                    "club": club,
                    "discipline": "handicap",
                    "targets": h_shot,
                    "hits": h_hit,
                }
            )

        d_shot = _int(cells[12])
        d_hit = _int(cells[13])
        if d_shot:
            events.append(
                {
                    "date": date,
                    "club": club,
                    "discipline": "doubles",
                    "targets": d_shot,
                    "hits": d_hit,
                }
            )

    return events


def _present_in_myata(source_item: dict, myata_events: list[dict]) -> tuple[bool, dict | None]:
    row = source_item["row"]

    for event in myata_events:
        if (
            event["date"] == source_item["event_date"]
            and event["discipline"] == source_item["discipline"]
            and event["targets"] == source_item["targets"]
            and event["hits"] == row["hits"]
        ):
            return True, event

    return False, None


def _group_reconciliation(result: dict) -> dict:
    grouped = {}
    for item in result.get("needs_reconciliation", []):
        candidate = item["candidate"]
        grouped.setdefault(
            candidate.ata_number,
            {
                "candidate": candidate,
                "items": [],
            },
        )["items"].append(item)
    return grouped


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile Central Zone source rows against exact MyATA 2026 "
            "Score Details instead of using a latest-date cutoff."
        )
    )
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    db = Database(DATA / "mntrapteam.db")

    print("MNTrapTeam Central Zone ↔ MyATA Exact Reconciliation")
    print("====================================================")
    print("READ ONLY — no database changes will be made.")
    print()

    central = central_discover(db, args.season)
    grouped = _group_reconciliation(central)

    print(
        f"Central Zone rows requiring exact reconciliation: "
        f"{sum(len(x['items']) for x in grouped.values())}"
    )
    print(f"Shooters requiring MyATA detail check: {len(grouped)}")
    print()

    if not grouped:
        print("Nothing to reconcile.")
        return 0

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

        page.goto(
            MYATA_URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print("Complete login if needed and leave Shooter Information Center open.")
        print("When ready, return here.")
        input("Press Enter to begin exact reconciliation... ")

        if context.pages:
            page = context.pages[-1]

        entries = list(grouped.values())

        for index, entry in enumerate(entries, 1):
            candidate = entry["candidate"]
            ata = candidate.ata_number
            name = candidate.display_name

            print()
            print(f"[{index}/{len(entries)}] {name} | ATA {ata}")

            try:
                _search_and_open(page, ata, name)
                page.wait_for_timeout(900)

                _open_year_detail(page, args.season)
                detail = _score_detail_table(page, args.season)
                detail_rows = _table_rows(detail)
                myata_events = _detail_events(detail_rows)

                for source_item in entry["items"]:
                    present, matched = _present_in_myata(
                        source_item,
                        myata_events,
                    )
                    row = source_item["row"]
                    status = "ALREADY IN MYATA" if present else "MISSING FROM MYATA"

                    results.append(
                        {
                            "candidate": candidate,
                            "source_item": source_item,
                            "present": present,
                            "matched": matched,
                        }
                    )

                    print(
                        f"  {status}: {source_item['event_date']} | "
                        f"{row['club']} | E{source_item['event_id']} "
                        f"{source_item['discipline']} "
                        f"{row['hits']}/{source_item['targets']}"
                    )

                    if present and matched:
                        print(
                            f"    MyATA detail: {matched['date']} | "
                            f"{matched['club']} | "
                            f"{matched['discipline']} "
                            f"{matched['hits']}/{matched['targets']}"
                        )

            except Exception as exc:
                print(f"  FAILED: {type(exc).__name__}: {exc}")
                for source_item in entry["items"]:
                    results.append(
                        {
                            "candidate": candidate,
                            "source_item": source_item,
                            "present": None,
                            "matched": None,
                        }
                    )

                try:
                    page.goto(
                        MYATA_URL,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                except Exception:
                    pass

        context.close()

    print()
    print("RECONCILIATION SUMMARY")
    print("----------------------")

    missing = [r for r in results if r["present"] is False]
    present = [r for r in results if r["present"] is True]
    failed = [r for r in results if r["present"] is None]

    print(f"Already represented in MyATA: {len(present)}")
    print(f"Missing from MyATA: {len(missing)}")
    print(f"Could not determine: {len(failed)}")

    if missing:
        print()
        print("MISSING CENTRAL ZONE ROWS — SAFE PROVISIONAL CANDIDATES")
        print("-------------------------------------------------------")
        for r in missing:
            item = r["source_item"]
            row = item["row"]
            print(
                f"{r['candidate'].ata_number} | "
                f"{r['candidate'].display_name} | "
                f"{item['event_date']} | {row['club']} | "
                f"E{item['event_id']} {item['discipline']} "
                f"{row['hits']}/{item['targets']}"
            )

    print()
    print("READ ONLY — no rows were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
