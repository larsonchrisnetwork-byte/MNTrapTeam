from mntrapteam.connectors import SessionStore, _load_playwright
from mntrapteam.paths import DATA

store = SessionStore(DATA)
profile = store.profile_dir("shootata")
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
    print("Open Search/Buddies and manually search for:")
    print("  ATA 2523333 - Aiden Weber")
    print()
    print("Stop when the search result containing Aiden is visible.")
    print("Do NOT open Aiden yet.")
    print()

    input("When Aiden is visible in the search results, press Enter here... ")

    if context.pages:
        page = context.pages[-1]

    print()
    print("VISIBLE INPUTS:")
    inputs = page.locator(
        'input:not([type="hidden"]), textarea, select'
    )

    for index in range(inputs.count()):
        item = inputs.nth(index)

        try:
            if not item.is_visible():
                continue

            print()
            print("INDEX:", index)
            print("tag:", item.evaluate("(e) => e.tagName"))
            print("type:", item.get_attribute("type"))
            print("name:", item.get_attribute("name"))
            print("id:", item.get_attribute("id"))
            print("placeholder:", item.get_attribute("placeholder"))
            print("aria:", item.get_attribute("aria-label"))
            print("value:", item.input_value() if item.evaluate(
                "(e) => ['INPUT','TEXTAREA','SELECT'].includes(e.tagName)"
            ) else "")
        except Exception as exc:
            print("input error:", exc)

    print()
    print("VISIBLE BUTTONS / CLICKABLE CONTROLS:")

    controls = page.locator(
        'button, a, [role="button"], [role="option"], [role="row"]'
    )

    for index in range(controls.count()):
        item = controls.nth(index)

        try:
            if not item.is_visible():
                continue

            text = " ".join(
                (item.inner_text(timeout=500) or "").split()
            )

            if (
                text
                or item.get_attribute("aria-label")
                or item.get_attribute("title")
            ):
                print()
                print("INDEX:", index)
                print("tag:", item.evaluate("(e) => e.tagName"))
                print("role:", item.get_attribute("role"))
                print("text:", text[:500])
                print("id:", item.get_attribute("id"))
                print("class:", item.get_attribute("class"))
                print("aria:", item.get_attribute("aria-label"))
                print("title:", item.get_attribute("title"))
        except Exception:
            pass

    print()
    print("TEXT CONTAINING AIDEN / 2523333:")

    body = page.locator("body").inner_text()

    for line in body.splitlines():
        upper = line.upper()

        if "AIDEN" in upper or "2523333" in upper:
            print(line)

    print()
    input("Press Enter to close the browser... ")

    context.close()
