from __future__ import annotations

from pathlib import Path
import json
import re
import time

from .connectors import SessionStore, _load_playwright
from .paths import DATA


def _clean(text: str) -> str:
    return "\n".join(
        line.strip()
        for line in str(text or "").splitlines()
        if line.strip()
    )


def inspect_other_shooter_dom(data_dir: Path = DATA) -> Path:
    store = SessionStore(data_dir)
    profile = store.profile_dir("shootata")

    root = Path(data_dir) / "connector_downloads" / "myata_dom"
    root.mkdir(parents=True, exist_ok=True)
    folder = root / time.strftime("%Y%m%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)

    sync_playwright = _load_playwright()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1500, "height": 1000},
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(
            "https://shootata.com/Shooter-Information-Center",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print()
        print("MyATA rendered-target inspector is running.")
        print("The browser stays open until YOU press Enter.")
        print()
        print("Please:")
        print("  1. Open Search/Buddies.")
        print("  2. Search ATA 2523333 (Aiden Weber).")
        print("  3. Open Aiden.")
        print("  4. Open his 2026 targets/statistics.")
        print("  5. Leave the 2026 target table visible.")
        print()
        input("When the 2026 targets are visible, return here and press Enter... ")

        if context.pages:
            page = context.pages[-1]

        page.wait_for_timeout(1000)

        body_text = _clean(page.locator("body").inner_text(timeout=10000))

        tables = []
        for index in range(page.locator("table").count()):
            table = page.locator("table").nth(index)
            try:
                text = _clean(table.inner_text(timeout=2000))
                headers = [
                    _clean(value)
                    for value in table.locator("th").all_inner_texts()
                ]
                rows = []
                tr = table.locator("tr")
                for row_index in range(min(tr.count(), 100)):
                    cells = tr.nth(row_index).locator("th,td").all_inner_texts()
                    rows.append([_clean(cell) for cell in cells])
                tables.append({
                    "index": index,
                    "headers": headers,
                    "rows": rows,
                    "text": text,
                })
            except Exception:
                pass

        custom_elements = page.evaluate(
            """() => {
                const names = new Set();
                for (const el of document.querySelectorAll('*')) {
                    if (el.tagName.includes('-')) {
                        names.add(el.tagName.toLowerCase());
                    }
                }
                return Array.from(names).sort();
            }"""
        )

        controls = []
        locator = page.locator(
            "button, a, input, select, [role=button], [role=tab]"
        )
        for index in range(min(locator.count(), 500)):
            item = locator.nth(index)
            try:
                controls.append({
                    "tag": item.evaluate("(el) => el.tagName.toLowerCase()"),
                    "text": _clean(item.inner_text(timeout=300) or ""),
                    "value": item.get_attribute("value") or "",
                    "name": item.get_attribute("name") or "",
                    "id": item.get_attribute("id") or "",
                    "aria": item.get_attribute("aria-label") or "",
                    "role": item.get_attribute("role") or "",
                })
            except Exception:
                pass

        # Save a sanitized HTML snapshot as well. It is local/gitignored and
        # intended only for selector development.
        html = page.content()
        (folder / "page.html").write_text(html, encoding="utf-8")
        (folder / "body_text.txt").write_text(body_text, encoding="utf-8")
        (folder / "tables.json").write_text(
            json.dumps(tables, indent=2),
            encoding="utf-8",
        )
        (folder / "controls.json").write_text(
            json.dumps(controls, indent=2),
            encoding="utf-8",
        )
        (folder / "custom_elements.json").write_text(
            json.dumps(custom_elements, indent=2),
            encoding="utf-8",
        )

        context.close()

    print()
    print(f"Capture directory: {folder}")
    print(f"Tables found: {len(tables)}")
    print(f"Custom elements found: {len(custom_elements)}")
    print()

    print("BODY TEXT LINES CONTAINING TARGET/2026/AIDEN:")
    for line in body_text.splitlines():
        upper = line.upper()
        if any(token in upper for token in (
            "2026",
            "AIDEN",
            "WEBER",
            "SINGLES",
            "HANDICAP",
            "DOUBLES",
            "TARGET",
            "AVERAGE",
        )):
            print(line)

    print()
    print("TABLES:")
    for table in tables:
        print()
        print(f"--- TABLE {table['index']} ---")
        print("Headers:", table["headers"])
        for row in table["rows"][:20]:
            print(row)

    print()
    print("CUSTOM ELEMENTS:")
    for name in custom_elements:
        if any(token in name for token in (
            "ata", "shooter", "score", "member", "search", "stat"
        )):
            print(name)

    return folder
