from __future__ import annotations

import re

from .connectors import SessionStore, _load_playwright
from .myata_bulk_dom_cli import MYATA_URL
from .paths import DATA


CANDIDATES = (
    ("1776550", "Craig Isaacson"),
    ("0416492", "Russ Hiltz"),
    ("2805615", "Troy Haverly"),
)


def _clean(value):
    return " ".join(str(value or "").split())


def _page_with_ata_field(context):
    for page in reversed(context.pages):
        try:
            field = page.locator('input[placeholder="ATA Number"]')
            if field.count() and field.first.is_visible():
                return page
        except Exception:
            continue

    # Second pass: tolerate a field that exists but Playwright currently
    # considers not visible; this helps identify the right page before retry.
    for page in reversed(context.pages):
        try:
            field = page.locator('input[placeholder="ATA Number"]')
            if field.count():
                return page
        except Exception:
            continue

    return None


def _find_ata_field(page):
    locator = page.locator('input[placeholder="ATA Number"]')
    if locator.count() < 1:
        raise RuntimeError("ATA Number input not found on selected MyATA page")

    field = locator.first

    try:
        if not field.is_visible():
            page.get_by_role("button", name="Search/Buddies").click(timeout=4000)
            page.wait_for_timeout(500)
    except Exception:
        pass

    locator = page.locator('input[placeholder="ATA Number"]')
    if locator.count() < 1:
        raise RuntimeError("ATA Number input disappeared after Search/Buddies open")

    return locator.first


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

        if not text:
            continue

        upper = text.upper()
        if upper in {
            "MY SCORES",
            "SEARCH/BUDDIES",
            "QUICK LIST",
            "ALL AMERICAN",
        }:
            continue

        if " - " in text and "," in text:
            rows.append(text)

    return rows


def _choose_result(rows, expected_name):
    if len(rows) == 1:
        return rows[0]

    last = expected_name.split()[-1].upper()

    matches = [row for row in rows if last in row.upper()]

    if len(matches) == 1:
        return matches[0]

    if not rows:
        raise RuntimeError("No Search/Buddies shooter result was visible")

    raise RuntimeError(
        f"Ambiguous Search/Buddies results: {len(rows)} result rows"
    )


def _parse_city_state(result_text):
    match = re.search(
        r"\s-\s(?P<city>.+?),\s*(?P<state>[A-Z]{2})\s*$",
        result_text,
        flags=re.IGNORECASE,
    )

    if not match:
        raise RuntimeError(
            f"Could not parse city/state from result: {result_text}"
        )

    return (
        _clean(match.group("city")),
        match.group("state").upper(),
    )


def main() -> int:
    store = SessionStore(DATA)
    profile = store.profile_dir("shootata")
    sync_playwright = _load_playwright()

    print("MNTrapTeam Northern Zone Candidate Residence Capture v6")
    print("======================================================")
    print("READ ONLY — database will not be changed.")
    print("Automatically selects the browser page containing the ATA field.")
    print()

    captured = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1500, "height": 1000},
            args=["--start-maximized"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        if not page.url or "shootata.com" not in page.url.lower():
            page.goto(
                MYATA_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

        print("Complete login if needed.")
        print("Open Search/Buddies and leave it visible.")
        input("When Search/Buddies is visible, press Enter... ")

        page = _page_with_ata_field(context)

        if page is None:
            print()
            print("OPEN PAGES:")
            for i, candidate_page in enumerate(context.pages):
                try:
                    print(f"  [{i}] {candidate_page.url}")
                except Exception:
                    print(f"  [{i}] <unavailable>")
            raise RuntimeError(
                "No open browser page contains an ATA Number field"
            )

        print(f"Using MyATA page: {page.url}")

        field = _find_ata_field(page)

        for pos, (ata, name) in enumerate(CANDIDATES, 1):
            print()
            print(f"[{pos}/{len(CANDIDATES)}] {name} | ATA {ata}")

            try:
                field.fill("")
                page.wait_for_timeout(250)
                field.fill(ata)

                page.wait_for_timeout(1800)
                rows = _visible_result_buttons(page)

                if not rows:
                    page.wait_for_timeout(1800)
                    rows = _visible_result_buttons(page)

                for row in rows:
                    print(f"  Visible result: {row}")

                result_text = _choose_result(rows, name)
                city, state = _parse_city_state(result_text)

                print(f"  Residence city/state: {city}, {state}")
                captured.append((ata, name, city, state))

            except Exception as exc:
                print(f"  FAILED: {exc}")

        print()
        print("RESIDENCE CAPTURE SUMMARY")
        print("-------------------------")

        if captured:
            for ata, name, city, state in captured:
                print(f"{ata} | {name} | {city}, {state}")
        else:
            print("No residences captured.")

        print()
        print("No Zone assignments were written.")

        input("Press Enter to close the browser... ")
        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
