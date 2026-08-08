from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .connectors import SessionStore, _load_playwright
from .paths import DATA


SOS_URL = "https://app.sosclays.com"
SOUTHERN_SHOOT_ID = "5220"


def _safe_name(value: str) -> str:
    keep = []
    for ch in value:
        if ch.isalnum() or ch in "-_.":
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep)[:180]


def main() -> int:
    store = SessionStore(DATA)
    profile = store.profile_dir("sos")
    sync_playwright = _load_playwright()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = (
        DATA
        / "connector_downloads"
        / "sos_zone"
        / f"southern_{SOUTHERN_SHOOT_ID}_{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    captured = []

    print("MNTrapTeam Southern Zone SOS Full-Report Capture")
    print("================================================")
    print(f"Target shoot ID: {SOUTHERN_SHOOT_ID}")
    print(f"Capture directory: {out_dir}")
    print()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1500, "height": 1000},
            args=["--start-maximized"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        def on_response(response):
            try:
                url = response.url
                if "sosclays" not in url.lower() and "appspot.com" not in url.lower():
                    return

                content_type = (
                    response.headers.get("content-type", "")
                    if response.headers
                    else ""
                ).lower()

                if "json" not in content_type:
                    return

                if (
                    SOUTHERN_SHOOT_ID not in url
                    and "highgun" not in url.lower()
                    and "shoot" not in url.lower()
                ):
                    return

                data = response.json()

                record = {
                    "url": url,
                    "status": response.status,
                    "method": response.request.method,
                    "content_type": content_type,
                    "data": data,
                }

                captured.append(record)

                filename = (
                    f"{len(captured):03d}_"
                    f"{_safe_name(url.split('/')[-1] or 'response')}.json"
                )
                (out_dir / filename).write_text(
                    json.dumps(record, indent=2),
                    encoding="utf-8",
                )

                print(
                    f"  CAPTURED {response.status} "
                    f"{response.request.method} {url}"
                )

            except Exception:
                pass

        context.on("response", on_response)

        if not page.url or "sosclays" not in page.url.lower():
            page.goto(
                SOS_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

        print()
        print("In the SOS browser:")
        print("  1. Log in if needed.")
        print("  2. Open All Shoots.")
        print("  3. Open 'MTA Southern Zone - 2026'.")
        print("  4. Open the full High Gun / HAA report.")
        print("  5. Leave the report visible.")
        print()
        input("When the Southern Zone report is visible, press Enter here... ")

        page.wait_for_timeout(1200)

        # Write an index summarizing all captured JSON.
        summary = {
            "shoot_id": SOUTHERN_SHOOT_ID,
            "captured_count": len(captured),
            "responses": [
                {
                    "url": item["url"],
                    "status": item["status"],
                    "method": item["method"],
                    "content_type": item["content_type"],
                }
                for item in captured
            ],
        }

        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )

        highgun = [
            item
            for item in captured
            if "highgun" in item["url"].lower()
            and SOUTHERN_SHOOT_ID in item["url"]
        ]

        print()
        print(f"Captured JSON responses: {len(captured)}")
        print(
            f"Southern shootHighGunReport responses: {len(highgun)}"
        )

        if highgun:
            print("SUCCESS: full Southern Zone report response captured.")
        else:
            print(
                "WARNING: no Southern shootHighGunReport response was captured."
            )

        print(f"Capture directory: {out_dir}")

        input("Press Enter to close the browser... ")
        context.close()

    return 0 if highgun else 2


if __name__ == "__main__":
    raise SystemExit(main())
