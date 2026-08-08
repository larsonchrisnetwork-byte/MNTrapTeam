from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import re
import time

from .connectors import SessionStore, _load_playwright
from .paths import DATA


SOS_HOME = "https://app.sosclays.com/"


@dataclass
class SOSCaptureResult:
    capture_directory: str
    pages_visited: int
    json_responses: int
    candidate_urls: int


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value[:80] or "item"


def _summary(value: Any) -> Any:
    """Keep response shape without dumping large/sensitive payloads."""
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:80]:
            if isinstance(item, list):
                result[key] = {
                    "type": "list",
                    "count": len(item),
                    "first_item_keys": (
                        list(item[0].keys())[:60]
                        if item and isinstance(item[0], dict)
                        else []
                    ),
                }
            elif isinstance(item, dict):
                result[key] = {
                    "type": "object",
                    "keys": list(item.keys())[:60],
                }
            else:
                result[key] = {
                    "type": type(item).__name__,
                }
        return result

    if isinstance(value, list):
        return {
            "type": "list",
            "count": len(value),
            "first_item_keys": (
                list(value[0].keys())[:60]
                if value and isinstance(value[0], dict)
                else []
            ),
        }

    return {"type": type(value).__name__}


def capture_sos_discovery(
    data_dir: Path = DATA,
    *,
    headed: bool = True,
) -> SOSCaptureResult:
    store = SessionStore(data_dir)
    profile = store.profile_dir("sos")
    output_root = Path(data_dir) / "connector_downloads" / "sos"
    output_root.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    capture_dir = output_root / stamp
    capture_dir.mkdir(parents=True, exist_ok=True)

    responses: list[dict[str, Any]] = []
    visited: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=not headed,
            viewport={"width": 1400, "height": 900},
            args=["--start-maximized"] if headed else [],
        )

        page = context.pages[0] if context.pages else context.new_page()

        def attach_page(target):
            def on_response(response):
                content_type = str(
                    response.headers.get("content-type", "")
                ).lower()

                url = response.url
                interesting_url = any(
                    token in url.lower()
                    for token in (
                        "api",
                        "shoot",
                        "event",
                        "score",
                        "result",
                        "leader",
                        "trophy",
                        "member",
                        "shooter",
                    )
                )

                if "json" not in content_type and not interesting_url:
                    return

                try:
                    body = response.json()
                except Exception:
                    return

                record = {
                    "url": url,
                    "status": response.status,
                    "method": response.request.method,
                    "content_type": content_type,
                    "shape": _summary(body),
                }

                # Preserve full JSON only in the local capture directory.
                # This directory is gitignored and should never be committed.
                index = len(responses) + 1
                filename = f"{index:03d}_{_safe_name(url.split('/')[-1])}.json"
                try:
                    (capture_dir / filename).write_text(
                        json.dumps(body, indent=2),
                        encoding="utf-8",
                    )
                    record["local_file"] = filename
                except Exception:
                    record["local_file"] = ""

                responses.append(record)

            target.on("response", on_response)

        for existing in context.pages:
            attach_page(existing)

        context.on("page", attach_page)

        page.goto(
            SOS_HOME,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print()
        print("SOS Clays discovery capture is running.")
        print("The browser will remain open until YOU press Enter.")
        print()
        print("In SOS Clays, locate and open these 2026 shoots:")
        print("  1. Minnesota Southern Zone")
        print("  2. Minnesota Central Zone")
        print("  3. Minnesota Northern Zone")
        print("  4. Minnesota State Shoot")
        print()
        print("For each shoot, open any page that shows:")
        print("  - events")
        print("  - shooter lists")
        print("  - scores/results")
        print("  - HAA/high-all-around, if SOS provides it")
        print()
        print("Take as much time as needed.")
        input("When you have visited all four shoots, return here and press Enter... ")

        for current in context.pages:
            try:
                visited.append(
                    {
                        "url": current.url,
                        "title": current.title(),
                    }
                )
            except Exception:
                pass

        # Capture visible links/buttons from the final page as route hints.
        ui = []
        try:
            active = context.pages[-1]
            controls = active.locator(
                "a, button, [role=button], input[type=button], input[type=submit]"
            )
            for index in range(min(controls.count(), 400)):
                control = controls.nth(index)
                try:
                    text = (
                        control.inner_text(timeout=500)
                        or control.get_attribute("aria-label")
                        or control.get_attribute("title")
                        or control.get_attribute("value")
                        or ""
                    )
                    text = " ".join(text.split())
                    href = control.get_attribute("href") or ""
                    if text or href:
                        ui.append({"text": text, "href": href})
                except Exception:
                    pass
        except Exception:
            pass

        (capture_dir / "response_index.json").write_text(
            json.dumps(responses, indent=2),
            encoding="utf-8",
        )
        (capture_dir / "visited_pages.json").write_text(
            json.dumps(visited, indent=2),
            encoding="utf-8",
        )
        (capture_dir / "final_controls.json").write_text(
            json.dumps(ui, indent=2),
            encoding="utf-8",
        )

        summary = {
            "capture_directory": str(capture_dir),
            "pages_visited": len(visited),
            "json_responses": len(responses),
            "candidate_urls": len({item["url"] for item in responses}),
            "responses": [
                {
                    "url": item["url"],
                    "status": item["status"],
                    "method": item["method"],
                    "shape": item["shape"],
                    "local_file": item["local_file"],
                }
                for item in responses
            ],
        }

        (capture_dir / "summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )

        context.close()

    return SOSCaptureResult(
        capture_directory=str(capture_dir),
        pages_visited=len(visited),
        json_responses=len(responses),
        candidate_urls=len({item["url"] for item in responses}),
    )
