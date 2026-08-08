from __future__ import annotations

import json
from pathlib import Path

from .paths import DATA


def _latest_capture():
    root = DATA / "connector_downloads" / "sos_zone"
    dirs = sorted(
        [p for p in root.iterdir() if p.is_dir() and p.name.startswith("southern_5220_")],
        key=lambda p: p.stat().st_mtime,
    )
    if not dirs:
        raise FileNotFoundError("No Southern Zone capture found")
    return dirs[-1]


def _report_file(capture):
    for path in sorted(capture.glob("*.json")):
        if "shootHighGunReport" in path.name:
            return path
    raise FileNotFoundError("No shootHighGunReport JSON in latest Southern capture")


def main() -> int:
    capture = _latest_capture()
    report_path = _report_file(capture)
    record = json.loads(report_path.read_text(encoding="utf-8"))

    data = record.get("data") or {}
    payload = data.get("payload") or {}

    rows = payload.get("sortedReportData") or []
    events = payload.get("eventsData") or []

    print("MNTrapTeam Southern Zone HAA Candidate Report")
    print("============================================")
    print(f"Capture: {capture}")
    print(f"Report rows: {len(rows)}")
    print(f"Events: {len(events)}")
    print()

    event_map = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        etype = int(event.get("eventTypeId") or 0)
        qty = int(event.get("targetQuantity") or 0)
        if int(event.get("haaEvent") or 0) != 1:
            continue
        if etype == 1:
            event_map["singles"] = qty
        elif etype == 3:
            event_map["handicap"] = qty
        elif etype == 2:
            event_map["doubles"] = qty

    required = {
        "singles": event_map.get("singles", 200),
        "handicap": event_map.get("handicap", 100),
        "doubles": event_map.get("doubles", 100),
    }

    print(
        f"HAA requirements from report: "
        f"S {required['singles']} | "
        f"H {required['handicap']} | "
        f"D {required['doubles']}"
    )
    print()

    complete = []
    partial = []

    # SOS high-gun rows do not expose per-event scores directly in the top-level
    # row; completion is represented by eventsCompleted. With exactly 3 HAA
    # events in this shoot, eventsCompleted==3 indicates all three were shot.
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("stateProvince") or "").upper() != "MN":
            continue

        events_completed = int(row.get("eventsCompleted") or 0)

        item = {
            "ata": str(row.get("ataId") or "").strip(),
            "name": " ".join(
                part for part in (
                    str(row.get("firstName") or "").strip(),
                    str(row.get("middleName") or "").strip(),
                    str(row.get("lastName") or "").strip(),
                ) if part
            ),
            "events_completed": events_completed,
            "total_score": int(row.get("totalScore") or 0),
        }

        if events_completed >= 3:
            complete.append(item)
        else:
            partial.append(item)

    complete.sort(key=lambda x: x["name"].upper())
    partial.sort(key=lambda x: x["name"].upper())

    print(f"Complete 3-event Southern HAA candidates: {len(complete)}")
    print(f"Partial/incomplete Southern shooters: {len(partial)}")
    print()

    print("COMPLETE SOUTHERN HAA CANDIDATES")
    print("-------------------------------")
    for item in complete:
        print(
            f"{item['ata']} | {item['name']} | "
            f"events={item['events_completed']} | total={item['total_score']}"
        )

    if partial:
        print()
        print("PARTIAL/INCOMPLETE")
        print("------------------")
        for item in partial:
            print(
                f"{item['ata']} | {item['name']} | "
                f"events={item['events_completed']} | total={item['total_score']}"
            )

    print()
    print(
        "NOTE: Candidate status means the shooter completed all three Southern "
        "HAA events. Residence must still be verified as Southern Zone before "
        "granting the HAA gate."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
