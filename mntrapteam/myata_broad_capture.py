from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import time

from .connectors import SessionStore, _load_playwright
from .paths import DATA


def _shape(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:100]:
            if isinstance(item, list):
                result[key] = {
                    "type": "list",
                    "count": len(item),
                    "first_item_keys": (
                        list(item[0].keys())[:80]
                        if item and isinstance(item[0], dict)
                        else []
                    ),
                }
            elif isinstance(item, dict):
                result[key] = {
                    "type": "object",
                    "keys": list(item.keys())[:80],
                }
            else:
                result[key] = {"type": type(item).__name__}
        return result

    if isinstance(value, list):
        return {
            "type": "list",
            "count": len(value),
            "first_item_keys": (
                list(value[0].keys())[:80]
                if value and isinstance(value[0], dict)
                else []
            ),
        }

    return {"type": type(value).__name__}


def capture_all_myata_json(data_dir: Path = DATA) -> Path:
    store = SessionStore(data_dir)
    profile = store.profile_dir("shootata")

    output_root = Path(data_dir) / "connector_downloads" / "myata_other"
    output_root.mkdir(parents=True, exist_ok=True)
    folder = output_root / time.strftime("%Y%m%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)

    records = []
    full_bodies = []
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

            # Restrict collection to ATA-owned traffic.
            if "shootata.com" not in url.lower():
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
            full_bodies.append({
                "url": url,
                "body": body,
            })

        context.on("response", on_response)

        page.goto(
            "https://shootata.com/Shooter-Information-Center",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print()
        print("Broad MyATA JSON capture is running.")
        print("The browser will stay open until YOU press Enter.")
        print()
        print("Please do exactly this:")
        print("  1. Open Search/Buddies.")
        print("  2. Search ATA 2523333 (Aiden Weber).")
        print("  3. Open Aiden.")
        print("  4. Open his 2026 targets/statistics.")
        print("  5. Switch to another year and back to 2026 if possible.")
        print()
        input("When Aiden's 2026 targets are visible, return here and press Enter... ")

        (folder / "summary.json").write_text(
            json.dumps(records, indent=2),
            encoding="utf-8",
        )

        # Full bodies remain only in the gitignored local capture folder.
        (folder / "responses.json").write_text(
            json.dumps(full_bodies, indent=2),
            encoding="utf-8",
        )

        context.close()

    print()
    print(f"Captured shootata.com JSON responses: {len(records)}")
    print(f"Capture directory: {folder}")

    for index, record in enumerate(records, 1):
        print()
        print(f"--- RESPONSE {index} ---")
        print("URL:", record["url"])
        print("HTTP:", record["status"])
        print("Method:", record["method"])
        print("Shape:", json.dumps(record["shape"], indent=2))

    return folder
