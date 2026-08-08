from __future__ import annotations

from pathlib import Path
import json
import time

from .connectors import SessionStore, _load_playwright
from .paths import DATA


INTERESTING = (
    "ShooterInformationCenter",
    "GetMember",
    "Search",
    "Buddy",
    "QuickList",
)


def _shape(body):
    if isinstance(body, dict):
        result = {}
        for key, value in body.items():
            if isinstance(value, list):
                result[key] = {
                    "type": "list",
                    "count": len(value),
                    "first_item_keys": (
                        list(value[0].keys())[:60]
                        if value and isinstance(value[0], dict)
                        else []
                    ),
                }
            elif isinstance(value, dict):
                result[key] = {
                    "type": "object",
                    "keys": list(value.keys())[:60],
                }
            else:
                result[key] = {"type": type(value).__name__}
        return result
    if isinstance(body, list):
        return {
            "type": "list",
            "count": len(body),
            "first_item_keys": (
                list(body[0].keys())[:60]
                if body and isinstance(body[0], dict)
                else []
            ),
        }
    return {"type": type(body).__name__}


def capture_other_shooter_lookup(data_dir: Path = DATA):
    store = SessionStore(data_dir)
    profile = store.profile_dir("shootata")

    root = Path(data_dir) / "connector_downloads" / "myata_search"
    root.mkdir(parents=True, exist_ok=True)
    folder = root / time.strftime("%Y%m%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)

    records = []
    sync_playwright = _load_playwright()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        def on_response(response):
            url = response.url
            if not any(token.lower() in url.lower() for token in INTERESTING):
                return
            try:
                body = response.json()
            except Exception:
                return

            record = {
                "url": url,
                "status": response.status,
                "method": response.request.method,
                "shape": _shape(body),
            }
            records.append(record)

        context.on("response", on_response)

        page.goto(
            "https://shootata.com/Shooter-Information-Center",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print()
        print("MyATA other-shooter lookup capture is running.")
        print("The browser will stay open until YOU press Enter.")
        print()
        print("In Shooter Information Center:")
        print("  1. Open Search/Buddies.")
        print("  2. Search for ATA 2523333 (Aiden Weber).")
        print("  3. Open whatever shooter detail/scores view is available.")
        print("  4. If possible, view the 2026 statistics or scores.")
        print()
        input("When finished, return here and press Enter... ")

        (folder / "summary.json").write_text(
            json.dumps(records, indent=2),
            encoding="utf-8",
        )

        context.close()

    print()
    print(f"Captured relevant JSON responses: {len(records)}")
    print(f"Capture directory: {folder}")

    for i, record in enumerate(records, 1):
        print()
        print(f"--- RESPONSE {i} ---")
        print("URL:", record["url"])
        print("HTTP:", record["status"])
        print("Method:", record["method"])
        print("Shape:", json.dumps(record["shape"], indent=2))

    return folder
