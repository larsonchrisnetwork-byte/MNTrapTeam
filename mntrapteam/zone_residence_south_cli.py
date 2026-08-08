from __future__ import annotations

import json
import re
from pathlib import Path

from .connectors import SessionStore, _load_playwright
from .myata_bulk_dom_cli import MYATA_URL
from .paths import DATA


def _clean(value):
    return " ".join(str(value or "").split())


def _latest_southern_capture():
    root = DATA / "connector_downloads" / "sos_zone"
    dirs = sorted(
        [p for p in root.iterdir() if p.is_dir() and p.name.startswith("southern_5220_")],
        key=lambda p: p.stat().st_mtime,
    )
    if not dirs:
        raise FileNotFoundError("No Southern Zone capture found")
    return dirs[-1]


def _load_candidates():
    capture = _latest_southern_capture()
    report = next(
        (p for p in sorted(capture.glob("*.json")) if "shootHighGunReport" in p.name),
        None,
    )
    if report is None:
        raise FileNotFoundError("No Southern shootHighGunReport JSON found")

    record = json.loads(report.read_text(encoding="utf-8"))
    payload = (record.get("data") or {}).get("payload") or {}
    rows = payload.get("sortedReportData") or []

    candidates = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("stateProvince") or "").upper() != "MN":
            continue
        if int(row.get("eventsCompleted") or 0) < 3:
            continue

        ata = str(row.get("ataId") or "").strip()
        if not ata or not ata.isdigit():
            continue

        name = " ".join(
            part for part in (
                str(row.get("firstName") or "").strip(),
                str(row.get("middleName") or "").strip(),
                str(row.get("lastName") or "").strip(),
            )
            if part
        )

        candidates.append((ata, name))

    candidates.sort(key=lambda x: x[1].upper())
    return candidates


def _page_with_ata_field(context):
    for page in reversed(context.pages):
        try:
            loc = page.locator('input[placeholder="ATA Number"]')
            if loc.count() and loc.first.is_visible():
                return page
        except Exception:
            continue

    for page in reversed(context.pages):
        try:
            if "shootata.com" not in (page.url or "").lower():
                continue
            try:
                page.get_by_role("button", name="Search/Buddies").click(timeout=4000)
                page.wait_for_timeout(700)
            except Exception:
                pass
            loc = page.locator('input[placeholder="ATA Number"]')
            if loc.count():
                return page
        except Exception:
            continue

    candidate = None
    for page in reversed(context.pages):
        try:
            if "shootata.com" in (page.url or "").lower():
                candidate = page
                break
        except Exception:
            continue

    if candidate is None:
        candidate = context.new_page()

    try:
        candidate.goto(MYATA_URL, wait_until="domcontentloaded", timeout=60000)
        candidate.wait_for_timeout(700)
        try:
            candidate.get_by_role("button", name="Search/Buddies").click(timeout=5000)
            candidate.wait_for_timeout(700)
        except Exception:
            pass
        loc = candidate.locator('input[placeholder="ATA Number"]')
        if loc.count():
            return candidate
    except Exception:
        pass

    return None


def _visible_result_buttons(page):
    rows = []
    buttons = page.locator("button")

    for i in range(buttons.count()):
        b = buttons.nth(i)
        try:
            if not b.is_visible():
                continue
            text = _clean(b.inner_text(timeout=500))
        except Exception:
            continue

        if not text or " - " not in text or "," not in text:
            continue

        upper = text.upper()
        if upper in {"MY SCORES", "SEARCH/BUDDIES", "QUICK LIST", "ALL AMERICAN"}:
            continue

        rows.append(text)

    return rows


def _choose_result(rows, expected_name):
    if len(rows) == 1:
        return rows[0]

    last = expected_name.split()[-1].upper() if expected_name.split() else ""
    matches = [row for row in rows if last and last in row.upper()]

    if len(matches) == 1:
        return matches[0]

    if not rows:
        raise RuntimeError("No Search/Buddies shooter result was visible")

    raise RuntimeError(f"Ambiguous Search/Buddies results: {len(rows)} rows")


def _parse_city_state(result_text):
    match = re.search(
        r"\s-\s(?P<city>.+?),\s*(?P<state>[A-Z]{2})\s*$",
        result_text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise RuntimeError(f"Could not parse city/state from: {result_text}")
    return _clean(match.group("city")), match.group("state").upper()


def main() -> int:
    candidates = _load_candidates()

    store = SessionStore(DATA)
    profile = store.profile_dir("shootata")
    sync_playwright = _load_playwright()

    out_dir = DATA / "connector_downloads" / "zone_residence"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "southern_2026_residences.json"

    print("MNTrapTeam Southern Zone Candidate Residence Capture")
    print("===================================================")
    print(f"Candidates: {len(candidates)}")
    print("READ ONLY — shooter/zone database tables are not changed.")
    print()

    captured = []
    failed = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1500, "height": 1000},
            args=["--start-maximized"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        if not page.url or "shootata.com" not in page.url.lower():
            page.goto(MYATA_URL, wait_until="domcontentloaded", timeout=60000)

        print("Complete login if needed.")
        print("Open Search/Buddies and leave it visible.")
        input("When Search/Buddies is visible, press Enter... ")

        page = _page_with_ata_field(context)
        if page is None:
            print()
            print("OPEN BROWSER PAGES CHECKED:")
            for index, candidate_page in enumerate(context.pages):
                try:
                    print(f"  [{index}] {candidate_page.url}")
                except Exception:
                    print(f"  [{index}] <unavailable>")
            raise RuntimeError(
                "Could not open/find the MyATA Search/Buddies ATA Number field"
            )

        print(f"Using MyATA page: {page.url}")
        field = page.locator('input[placeholder="ATA Number"]').first

        for pos, (ata, name) in enumerate(candidates, 1):
            print()
            print(f"[{pos}/{len(candidates)}] {name} | ATA {ata}")

            try:
                field.fill("")
                page.wait_for_timeout(250)
                field.fill(ata)
                page.wait_for_timeout(1700)

                rows = _visible_result_buttons(page)

                if not rows:
                    page.wait_for_timeout(1700)
                    rows = _visible_result_buttons(page)

                result = _choose_result(rows, name)
                city, state = _parse_city_state(result)

                print(f"  {result}")
                print(f"  Residence: {city}, {state}")

                captured.append({
                    "ata": ata,
                    "name": name,
                    "city": city,
                    "state": state,
                    "result_text": result,
                })

            except Exception as exc:
                print(f"  FAILED: {exc}")
                failed.append({
                    "ata": ata,
                    "name": name,
                    "error": str(exc),
                })

        output = {
            "season": 2026,
            "zone_shoot": "Southern",
            "shoot_id": 5220,
            "captured": captured,
            "failed": failed,
        }

        out_file.write_text(
            json.dumps(output, indent=2),
            encoding="utf-8",
        )

        print()
        print("SOUTHERN RESIDENCE SUMMARY")
        print("--------------------------")
        for item in captured:
            print(
                f"{item['ata']} | {item['name']} | "
                f"{item['city']}, {item['state']}"
            )

        print()
        print(f"Captured: {len(captured)}")
        print(f"Failed: {len(failed)}")
        print(f"Saved: {out_file}")
        print()
        print(
            "No Southern Zone qualifications were written yet. "
            "Residence must be mapped against the official MTA zone boundary first."
        )

        input("Press Enter to close the browser... ")
        context.close()

    return 0 if captured else 2


if __name__ == "__main__":
    raise SystemExit(main())
