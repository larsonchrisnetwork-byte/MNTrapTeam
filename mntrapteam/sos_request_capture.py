from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import time

from .connectors import SessionStore, _load_playwright
from .paths import DATA


SOS_STATE_URL_HINT = "shootHighGunReport"


def _sanitize_post_data(value: str | None) -> Any:
    if not value:
        return None

    text = value.strip()

    try:
        parsed = json.loads(text)
    except Exception:
        return text[:5000]

    sensitive_tokens = (
        "token",
        "password",
        "email",
        "phone",
        "address",
        "authorization",
    )

    def clean(item):
        if isinstance(item, dict):
            result = {}
            for key, val in item.items():
                if any(token in str(key).lower() for token in sensitive_tokens):
                    result[key] = "<redacted>"
                else:
                    result[key] = clean(val)
            return result
        if isinstance(item, list):
            return [clean(val) for val in item]
        return item

    return clean(parsed)


def capture_highgun_request(
    data_dir: Path = DATA,
) -> Path:
    store = SessionStore(data_dir)
    profile = store.profile_dir("sos")

    output_root = Path(data_dir) / "connector_downloads" / "sos_request"
    output_root.mkdir(parents=True, exist_ok=True)

    capture_dir = output_root / time.strftime("%Y%m%d_%H%M%S")
    capture_dir.mkdir(parents=True, exist_ok=True)

    records = []
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--start-maximized"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        def on_request(request):
            if SOS_STATE_URL_HINT.lower() not in request.url.lower():
                return

            record = {
                "url": request.url,
                "method": request.method,
                "post_data": _sanitize_post_data(request.post_data),
                "headers": {
                    key: "<redacted>"
                    if key.lower() in {"authorization", "cookie"}
                    else value
                    for key, value in request.headers.items()
                    if key.lower() in {
                        "content-type",
                        "origin",
                        "referer",
                        "authorization",
                        "cookie",
                    }
                },
            }
            records.append(record)

        context.on("request", on_request)

        page.goto(
            "https://app.sosclays.com/",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print()
        print("SOS High-Gun request capture is running.")
        print()
        print("Open the 2026 MN State Shoot.")
        print("Open the HAA / High-All-Around report exactly as before.")
        print("If filters must be selected, select the HAA view.")
        print()
        input(
            "When the HAA report is visible, return here and press Enter... "
        )

        (capture_dir / "highgun_requests.json").write_text(
            json.dumps(records, indent=2),
            encoding="utf-8",
        )

        context.close()

    print()
    print(f"Captured High-Gun requests: {len(records)}")
    print(f"Capture directory: {capture_dir}")

    for index, record in enumerate(records, 1):
        print()
        print(f"--- REQUEST {index} ---")
        print("URL:", record["url"])
        print("Method:", record["method"])
        print("POST DATA:")
        print(json.dumps(record["post_data"], indent=2))

    return capture_dir
