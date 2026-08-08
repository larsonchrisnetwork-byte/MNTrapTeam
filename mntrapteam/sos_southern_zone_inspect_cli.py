from __future__ import annotations

import json
from pathlib import Path

from .paths import DATA


def main() -> int:
    root = DATA / "connector_downloads" / "sos_zone"

    if not root.exists():
        print("No sos_zone captures found.")
        return 2

    dirs = sorted(
        [p for p in root.iterdir() if p.is_dir() and p.name.startswith("southern_5220_")],
        key=lambda p: p.stat().st_mtime,
    )

    if not dirs:
        print("No Southern 5220 captures found.")
        return 2

    latest = dirs[-1]
    print(f"Using capture: {latest}")

    files = sorted(latest.glob("*.json"))
    found = 0

    for path in files:
        if path.name == "summary.json":
            continue

        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        url = str(record.get("url") or "")
        data = record.get("data")

        if "5220" not in url or "highgun" not in url.lower():
            continue

        found += 1
        print()
        print(f"REPORT FILE: {path.name}")
        print(f"URL: {url}")

        payload = data.get("payload") if isinstance(data, dict) else None

        if not isinstance(payload, dict):
            print("Payload is not an object.")
            continue

        print("Payload keys:", sorted(payload.keys()))

        rows = payload.get("sortedReportData")
        events = payload.get("eventsData")

        print(
            "sortedReportData rows:",
            len(rows) if isinstance(rows, list) else "not-list",
        )
        print(
            "eventsData rows:",
            len(events) if isinstance(events, list) else "not-list",
        )

        if isinstance(events, list):
            print()
            print("EVENTS:")
            for event in events:
                if not isinstance(event, dict):
                    continue
                print(
                    f"  #{event.get('eventNumber')} | "
                    f"{event.get('name')} | "
                    f"type={event.get('eventTypeId')} | "
                    f"targets={event.get('targetQuantity')} | "
                    f"haa={event.get('haaEvent')}"
                )

        if isinstance(rows, list):
            mn_rows = [
                row
                for row in rows
                if isinstance(row, dict)
                and str(row.get("stateProvince") or "").upper() == "MN"
            ]
            print()
            print(f"Minnesota report rows: {len(mn_rows)}")

    if not found:
        print("No Southern 5220 HighGun report JSON found in latest capture.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
