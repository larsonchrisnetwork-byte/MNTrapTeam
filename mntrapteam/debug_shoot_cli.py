from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .shootscoreboard_web import BASE_URL, fetch_text, parse_shoot_header
from .recent_score_scout_cli import (
    _event_specs_from_entries,
    _parse_report_relaxed,
)


def inspect_shoot(shoot_id: int, name_filter: str = "", dump_path: str = "") -> int:
    menu_url = f"{BASE_URL}menu.cfm?shootid={shoot_id}"
    entries_url = f"{BASE_URL}entrys.cfm?shootid={shoot_id}"

    print(f"MNTrapTeam ShootScoreBoard Single-Shoot Diagnostic")
    print("==================================================")
    print(f"Shoot ID: {shoot_id}")
    print()

    menu_html = fetch_text(menu_url, timeout=8)
    shoot_name, start_date, end_date = parse_shoot_header(menu_html, shoot_id)

    print(f"Shoot: {shoot_name}")
    print(f"Dates: {start_date} through {end_date}")
    print(f"Menu: {menu_url}")
    print()

    entries_html = fetch_text(entries_url, timeout=8)
    specs = _event_specs_from_entries(entries_html)

    if not specs:
        print("No S/H/D events found on Event Entries page.")
        return 2

    print("EVENTS FOUND")
    print("------------")
    for event_id, discipline in specs:
        print(f"E{event_id} | {discipline}")
    print()

    all_rows = []
    filter_upper = str(name_filter or "").upper()

    for event_id, discipline in specs:
        report_url = f"{BASE_URL}reports.cfm?shootid={shoot_id}&sorteventid={event_id}"
        print(f"Loading E{event_id} {discipline}...")
        print(f"  {report_url}")

        try:
            html = fetch_text(report_url, timeout=8)
            event = _parse_report_relaxed(html, event_id, discipline)
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            continue

        print(f"  Parsed rows: {len(event.entries)}")
        print(f"  Event name: {event.name}")

        matched = 0
        for row in event.entries:
            all_rows.append(
                {
                    "shoot_id": shoot_id,
                    "shoot_name": shoot_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "event_id": event_id,
                    "event_name": event.name,
                    "discipline": discipline,
                    "name": row["name"],
                    "state": row["state"],
                    "hits": row["hits"],
                    "targets": row["targets"],
                }
            )

            if filter_upper and filter_upper in str(row["name"]).upper():
                matched += 1
                print(
                    f"    MATCH: {row['name']} | {row['state']} | "
                    f"{row['hits']}/{row['targets']}"
                )

        if filter_upper:
            print(f"  Rows matching '{name_filter}': {matched}")
        print()

    print("SUMMARY")
    print("-------")
    print(f"Total parsed score rows: {len(all_rows)}")

    if filter_upper:
        matches = [
            row for row in all_rows
            if filter_upper in str(row["name"]).upper()
        ]
        print(f"Total rows matching '{name_filter}': {len(matches)}")

    if dump_path:
        out = Path(dump_path)
        if not out.is_absolute():
            out = Path.cwd() / out
        out.parent.mkdir(parents=True, exist_ok=True)

        fields = [
            "shoot_id",
            "shoot_name",
            "start_date",
            "end_date",
            "event_id",
            "event_name",
            "discipline",
            "name",
            "state",
            "hits",
            "targets",
        ]
        with out.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"CSV dump: {out}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect one ShootScoreBoard shoot without scanning other shoots."
    )
    parser.add_argument("shoot_id", type=int)
    parser.add_argument(
        "--name",
        default="",
        help="Print only matching-name diagnostics, e.g. LARSON",
    )
    parser.add_argument(
        "--dump",
        default="",
        help="Optional CSV output path containing every parsed score row",
    )
    args = parser.parse_args()

    return inspect_shoot(
        args.shoot_id,
        name_filter=args.name,
        dump_path=args.dump,
    )


if __name__ == "__main__":
    raise SystemExit(main())
