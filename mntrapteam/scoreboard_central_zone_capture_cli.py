from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .connectors import _load_playwright
from .paths import DATA


START_URL = "https://www.shootscoreboard.com/"


def _clean(value):
    return " ".join(str(value or "").split())


def main() -> int:
    profile = DATA / "browser_profiles" / "shootscoreboard"
    profile.mkdir(parents=True, exist_ok=True)
    sync_playwright = _load_playwright()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = (
        DATA
        / "connector_downloads"
        / "scoreboard_zone"
        / f"central_beaverbrook_{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    print("MNTrapTeam Central Zone ShootScoreBoard Capture")
    print("===============================================")
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

        if not page.url or "shootscoreboard.com" not in page.url.lower():
            page.goto(
                START_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

        print("In ShootScoreBoard:")
        print("  1. Find the 2026 MTA Central Zone / Beaverbrook shoot.")
        print("  2. Open the shoot page.")
        print("  3. Open the most complete results / high-gun / HAA view available.")
        print("  4. Leave that results page visible.")
        print()
        input("When the Central Zone results are visible, press Enter here... ")

        if context.pages:
            # Choose the last ShootScoreBoard page/tab.
            for candidate in reversed(context.pages):
                try:
                    if "shootscoreboard.com" in (candidate.url or "").lower():
                        page = candidate
                        break
                except Exception:
                    pass

        page.wait_for_timeout(800)

        html = page.content()
        body = _clean(page.locator("body").inner_text(timeout=5000))

        (out_dir / "page.html").write_text(html, encoding="utf-8")
        (out_dir / "body.txt").write_text(body, encoding="utf-8")

        links = []
        anchors = page.locator("a")

        for i in range(anchors.count()):
            a = anchors.nth(i)
            try:
                text = _clean(a.inner_text(timeout=200))
                href = a.get_attribute("href")
            except Exception:
                continue

            if not href:
                continue

            links.append({
                "text": text,
                "href": href,
            })

        buttons = []
        btns = page.locator("button, input[type=button], input[type=submit]")

        for i in range(btns.count()):
            el = btns.nth(i)
            try:
                if not el.is_visible():
                    continue
                text = _clean(el.inner_text(timeout=200))
                value = el.get_attribute("value")
            except Exception:
                continue

            buttons.append({
                "text": text,
                "value": value,
            })

        forms = []
        fs = page.locator("form")

        for i in range(fs.count()):
            f = fs.nth(i)
            try:
                action = f.get_attribute("action")
                method = f.get_attribute("method")
            except Exception:
                continue

            forms.append({
                "action": action,
                "method": method,
            })

        meta = {
            "url": page.url,
            "title": page.title(),
            "links": links,
            "buttons": buttons,
            "forms": forms,
        }

        (out_dir / "page_meta.json").write_text(
            json.dumps(meta, indent=2),
            encoding="utf-8",
        )

        print()
        print(f"Captured URL: {page.url}")
        print(f"Page title: {page.title()}")
        print(f"Links captured: {len(links)}")
        print(f"Buttons captured: {len(buttons)}")
        print(f"Forms captured: {len(forms)}")
        print()

        print("RESULT-LIKE LINKS")
        print("-----------------")

        interesting = []

        for link in links:
            hay = (
                str(link.get("text") or "")
                + " "
                + str(link.get("href") or "")
            ).upper()

            if any(
                token in hay
                for token in (
                    "RESULT",
                    "REPORT",
                    "HIGH",
                    "HAA",
                    "SINGLE",
                    "HANDICAP",
                    "DOUBLE",
                    "SHOOTID",
                    "SCORES",
                )
            ):
                interesting.append(link)
                print(
                    f"{link.get('text')!r} -> {link.get('href')}"
                )

        print()
        print(f"Interesting links: {len(interesting)}")
        print(f"Capture directory: {out_dir}")
        print()
        print(
            "Next step: inspect this capture and identify the full-participant "
            "Central Zone report endpoint/page."
        )

        input("Press Enter to close the browser... ")
        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
