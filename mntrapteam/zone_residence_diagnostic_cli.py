from __future__ import annotations

from .connectors import SessionStore, _load_playwright
from .myata_bulk_dom_cli import MYATA_URL
from .paths import DATA


TEST_ATA = "1776550"
TEST_NAME = "Craig Isaacson"


def _clean(value):
    return " ".join(str(value or "").split())


def main() -> int:
    store = SessionStore(DATA)
    profile = store.profile_dir("shootata")
    sync_playwright = _load_playwright()

    print("MNTrapTeam Search/Buddies Residence Diagnostic")
    print("==============================================")
    print("READ ONLY — nothing will be clicked after search.")
    print()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1500, "height": 1000},
            args=["--start-maximized"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(MYATA_URL, wait_until="domcontentloaded", timeout=60000)

        print("Complete login if needed.")
        input("When Search/Buddies is visible, press Enter... ")

        if context.pages:
            page = context.pages[-1]

        try:
            page.get_by_role("button", name="Search/Buddies").click(timeout=5000)
        except Exception:
            pass

        page.wait_for_timeout(400)

        print()
        print("VISIBLE INPUTS BEFORE SEARCH:")
        inputs = page.locator("input")

        visible_inputs = []
        for i in range(inputs.count()):
            el = inputs.nth(i)
            try:
                if not el.is_visible():
                    continue
            except Exception:
                continue

            attrs = {}
            for attr in ("type", "name", "id", "placeholder", "aria-label"):
                try:
                    attrs[attr] = el.get_attribute(attr)
                except Exception:
                    attrs[attr] = None

            try:
                value = el.input_value()
            except Exception:
                value = ""

            print(f"INDEX {i}: attrs={attrs} value={value!r}")
            visible_inputs.append((i, el, attrs))

        if not visible_inputs:
            raise RuntimeError("No visible inputs found")

        # First try a field explicitly identifying itself as ATA.
        target = None
        for i, el, attrs in visible_inputs:
            haystack = " ".join(str(v or "") for v in attrs.values()).upper()
            if "ATA" in haystack:
                target = (i, el)
                break

        # If no attribute identifies the ATA field, do not guess silently.
        if target is None:
            print()
            print("No input explicitly identified itself as ATA.")
            print("Falling back to the last visible input for this diagnostic only.")
            target = (visible_inputs[-1][0], visible_inputs[-1][1])

        idx, ata_input = target
        print()
        print(f"Filling input INDEX {idx} with ATA {TEST_ATA}")

        try:
            ata_input.fill("")
            ata_input.fill(TEST_ATA)
        except Exception as exc:
            print("Fill failed:", exc)

        page.wait_for_timeout(1500)

        print()
        print("VISIBLE BUTTONS / CLICKABLE RESULT-LIKE CONTROLS AFTER SEARCH:")
        buttons = page.locator("button")

        found = 0
        for i in range(buttons.count()):
            el = buttons.nth(i)
            try:
                if not el.is_visible():
                    continue
                text = _clean(el.inner_text(timeout=400))
            except Exception:
                continue

            if not text:
                continue

            print(f"BUTTON {i}: {text}")
            found += 1

        print()
        print("BODY LINES CONTAINING CRAIG / ISAACSON / 1776550 / MN:")
        try:
            body = page.locator("body").inner_text(timeout=3000)
        except Exception:
            body = ""

        for line in body.splitlines():
            clean = _clean(line)
            upper = clean.upper()
            if any(token in upper for token in ("CRAIG", "ISAACSON", "1776550")):
                print(clean)

        print()
        print(f"Visible buttons printed: {found}")
        print("Do not click Craig. Copy this PowerShell output back to ChatGPT.")

        input("Press Enter to close the browser... ")
        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
