from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

from .database import Database
from .paths import DATA


ZONE_DEFS = {
    "Northern": {
        "shoot_id": "5542",
        "host": "Grand Rapids",
        "keywords": ("N ZONE", "NORTHERN ZONE"),
    },
    "Southern": {
        "shoot_id": "5220",
        "host": "Lester Prairie",
        "keywords": ("S ZONE", "SOUTHERN ZONE"),
    },
    "Central": {
        "shoot_id": None,
        "host": "Beaverbrook",
        "keywords": ("C ZONE", "CENTRAL ZONE", "BEAVERBROOK"),
    },
}


def _rows(db, sql, params=()):
    return [dict(r) for r in db.query(sql, params)]


def _score_inventory(db, keywords):
    clauses = []
    params = []
    for keyword in keywords:
        clauses.append("upper(COALESCE(event_name,'')) LIKE ?")
        params.append(f"%{keyword}%")

    where = " OR ".join(clauses)

    return _rows(
        db,
        f"""
        SELECT
            s.ata_number,
            s.display_name,
            sc.discipline,
            sc.event_name,
            sc.targets,
            sc.hits,
            sc.source
        FROM scores sc
        JOIN shooters s ON s.id=sc.shooter_id
        WHERE {where}
        ORDER BY s.display_name, sc.event_name
        """,
        tuple(params),
    )


def _walk_json(root):
    if not root.exists():
        return

    for path in root.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        yield path, data


def _contains_shoot_id(data, shoot_id):
    if not shoot_id:
        return False

    needle = str(shoot_id)

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in {"shootid", "shoot_id"} and str(child) == needle:
                    return True
                if walk(child):
                    return True
        elif isinstance(value, list):
            return any(walk(child) for child in value)
        return False

    return walk(data)


def _url_mentions(path, data, shoot_id):
    text = json.dumps(data)[:200000].lower()
    if shoot_id and shoot_id.lower() in text:
        return True
    return False


def _interesting_shape(data):
    if not isinstance(data, dict):
        return ""

    payload = data.get("payload")

    if isinstance(payload, dict):
        keys = set(payload)
        if "sortedReportData" in keys and "eventsData" in keys:
            return "high-gun-report"

    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            keys = set(first)
            if {"shootId", "name"}.issubset(keys):
                return "shoot-list"
            if {"userId", "firstName", "lastName"}.issubset(keys):
                return "participant-like"

    return ""


def _capture_inventory(zone_name, shoot_id):
    roots = [
        DATA / "connector_downloads" / "sos",
        DATA / "connector_downloads" / "sos_request",
    ]

    hits = []

    for root in roots:
        for path, data in _walk_json(root):
            shape = _interesting_shape(data)

            if _contains_shoot_id(data, shoot_id) or _url_mentions(path, data, shoot_id):
                hits.append((path, shape or "json"))

    return hits


def main() -> int:
    db = Database(DATA / "mntrapteam.db")

    print("MNTrapTeam 2026 Zone HAA Evidence Inventory")
    print("===========================================")
    print()

    for zone, info in ZONE_DEFS.items():
        print(zone.upper())
        print("-" * len(zone))

        score_rows = _score_inventory(db, info["keywords"])

        shooters = {
            (row.get("ata_number"), row.get("display_name"))
            for row in score_rows
        }

        print(f"Database zone-score rows: {len(score_rows)}")
        print(f"Distinct shooters with matching score rows: {len(shooters)}")

        by_event = defaultdict(int)
        for row in score_rows:
            by_event[str(row.get("event_name") or "")] += 1

        if by_event:
            print("Event names:")
            for event, count in sorted(by_event.items()):
                print(f"  {count:3d} | {event}")
        else:
            print("Event names: none")

        capture_hits = _capture_inventory(
            zone,
            info["shoot_id"],
        )

        print(f"Local SOS JSON files mentioning shoot: {len(capture_hits)}")

        for path, shape in capture_hits[:20]:
            try:
                rel = path.relative_to(DATA)
            except Exception:
                rel = path
            print(f"  {shape:16s} | {rel}")

        if len(capture_hits) > 20:
            print(f"  ... {len(capture_hits) - 20} more")

        if zone == "Central":
            print(
                "Central note: no SOS shoot_id is currently known; "
                "database/event-name inventory is the main local check."
            )

        print()

    print("Interpretation")
    print("--------------")
    print(
        "A winner PDF is not sufficient to identify all HAA completers. "
        "We need full-participant event data containing Singles, Handicap, "
        "and Doubles for each shooter."
    )
    print(
        "If Southern has a full SOS report locally, the next importer can "
        "derive all Southern HAA candidates directly."
    )
    print(
        "If Central has no full-participant evidence locally, the next step "
        "will be a dedicated Beaverbrook capture rather than using winners only."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
