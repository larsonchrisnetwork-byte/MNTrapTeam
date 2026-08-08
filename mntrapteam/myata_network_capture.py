from __future__ import annotations

from pathlib import Path
import json
import time

from .connectors import SessionStore, _load_playwright
from .paths import DATA


def capture_all_network(data_dir: Path = DATA) -> Path:
    store = SessionStore(data_dir)
    profile = store.profile_dir("shootata")

    out_root = Path(data_dir) / "connector_downloads" / "myata_network"
    out_root.mkdir(parents=True, exist_ok=True)
    folder = out_root / time.strftime("%Y%m%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)

    requests = []
    responses = []
    sync_playwright = _load_playwright()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        def on_request(request):
            requests.append({
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "frame_url": request.frame.url if request.frame else "",
            })

        def on_response(response):
            responses.append({
                "url": response.url,
                "status": response.status,
                "resource_type": response.request.resource_type,
                "content_type": response.headers.get("content-type", ""),
                "frame_url": response.request.frame.url if response.request.frame else "",
            })

        context.on("request", on_request)
        context.on("response", on_response)

        page.goto(
            "https://shootata.com/Shooter-Information-Center",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print()
        print("Full MyATA network capture is running.")
        print("The browser stays open until YOU press Enter.")
        print()
        print("Please:")
        print("  1. Open Search/Buddies.")
        print("  2. Search ATA 2523333 (Aiden Weber).")
        print("  3. Open Aiden.")
        print("  4. Open his 2026 targets/statistics.")
        print("  5. Change year away from 2026 and back to 2026 if possible.")
        print()
        input("When Aiden's 2026 targets are visible, return here and press Enter... ")

        frames = []
        for current_page in context.pages:
            for frame in current_page.frames:
                try:
                    frames.append({
                        "page_url": current_page.url,
                        "frame_url": frame.url,
                        "name": frame.name,
                    })
                except Exception:
                    pass

        payload = {
            "requests": requests,
            "responses": responses,
            "frames": frames,
        }

        (folder / "network.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        context.close()

    print()
    print(f"Requests captured: {len(requests)}")
    print(f"Responses captured: {len(responses)}")
    print(f"Frames captured: {len(frames)}")
    print(f"Capture directory: {folder}")
    print()

    interesting = []
    seen = set()

    for item in responses:
        key = (item["url"], item["resource_type"], item["content_type"])
        if key in seen:
            continue
        seen.add(key)

        if item["resource_type"] in {"xhr", "fetch", "document"}:
            interesting.append(item)
        elif any(token in item["url"].lower() for token in (
            "score", "target", "member", "shooter", "ata", "search", "buddy"
        )):
            interesting.append(item)

    print("INTERESTING RESPONSES:")
    for item in interesting:
        print(
            item["status"],
            item["resource_type"],
            item["content_type"],
            item["url"],
        )

    print()
    print("FRAMES:")
    for item in frames:
        print(item["frame_url"])

    return folder
