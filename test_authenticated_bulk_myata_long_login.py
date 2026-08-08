import re
from mntrapteam.database import Database
from mntrapteam.paths import DATA
from playwright.sync_api import sync_playwright

MYATA = "https://shootata.com/Shooter-Information-Center"
API_MARKER = "GetMemberStatsSummary"

db = Database(DATA / "mntrapteam.db")

candidates = db.query("""
SELECT DISTINCT
    s.ata_number,
    s.display_name
FROM haa_qualifications h
JOIN shooters s ON s.id=h.shooter_id
WHERE h.season=2026
  AND h.verified=1
  AND s.ata_number IS NOT NULL
  AND trim(s.ata_number)<>''
ORDER BY s.display_name
LIMIT 10
""")

profile = DATA / "browser_sessions" / "shootata"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=False,
        viewport={"width": 1400, "height": 900},
        args=["--start-maximized"],
    )

    page = context.pages[0] if context.pages else context.new_page()

    captured_headers = {}

    def on_request(request):
        if API_MARKER.lower() not in request.url.lower():
            return

        captured_headers.clear()
        captured_headers.update(dict(request.headers))

        print()
        print("Captured MyATA authenticated summary request.")
        print("URL:", request.url)
        print(
            "Authorization header present:",
            "authorization" in {
                k.lower(): v for k, v in request.headers.items()
            }
        )

    context.on("request", on_request)

    page.goto(
        MYATA,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    print()
    print("MyATA browser is open.")
    print()
    print("Take as much time as needed to:")
    print("  - enter username")
    print("  - enter password")
    print("  - complete MFA")
    print("  - handle password-manager prompts")
    print()
    print("Do NOT press Enter here until:")
    print("  Shooter Information Center is open")
    print("  and the My Scores button is visible.")
    print()

    input("When login is fully complete, return here and press Enter... ")

    if context.pages:
        page = context.pages[-1]

    page.wait_for_timeout(2000)

    controls = [
        page.get_by_text("My Scores", exact=True),
        page.get_by_role("button", name=re.compile("my scores", re.I)),
        page.locator('input[value*="My Scores" i]'),
        page.locator('a:has-text("My Scores")'),
    ]

    control = None

    for candidate in controls:
        try:
            if candidate.count() and candidate.first.is_visible():
                control = candidate.first
                break
        except Exception:
            pass

    if control is None:
        print()
        print("My Scores was not found automatically.")
        print("The browser will remain open.")
        print("Navigate manually until My Scores is visible.")
        input("Then return here and press Enter again... ")

        if context.pages:
            page = context.pages[-1]

        for candidate in controls:
            try:
                if candidate.count() and candidate.first.is_visible():
                    control = candidate.first
                    break
            except Exception:
                pass

    if control is None:
        raise RuntimeError("My Scores control still could not be found.")

    print()
    print("Clicking My Scores...")

    control.click()
    page.wait_for_timeout(8000)

    if not captured_headers:
        print()
        print("No authenticated stats request captured yet.")
        print("The browser will remain open.")
        print("Click My Scores manually or refresh the score view.")
        input("After your scores load, return here and press Enter... ")

    if not captured_headers:
        raise RuntimeError(
            "No GetMemberStatsSummary request was captured."
        )

    useful = {}

    for key, value in captured_headers.items():
        lower = key.lower()

        if lower in {
            "authorization",
            "accept",
            "content-type",
            "origin",
            "referer",
            "x-requested-with",
        } or lower.startswith("x-"):
            useful[key] = value

    print()
    print("Authenticated MyATA context captured.")
    print("Testing other HAA qualifiers...")
    print()

    tested = 0

    for shooter in candidates:
        ata = str(shooter["ata_number"]).strip()

        if ata == "0113918":
            continue

        url = (
            "https://shootata.com/API/ATA_Modules/"
            "ShooterInformationCenter/"
            "GetMemberStatsSummary?ataNumber="
            + ata
        )

        response = context.request.get(
            url,
            headers=useful,
            timeout=30000,
        )

        print(
            shooter["display_name"],
            "| ATA", ata,
            "| HTTP", response.status,
        )

        if response.status == 200:
            body = response.json()

            season = None

            if isinstance(body, list):
                for item in body:
                    if str(item.get("Year")) == "2026":
                        season = item
                        break

            if season:
                print(
                    "   Singles:",
                    season.get("SinglesShot"),
                    "@",
                    season.get("SinglesHitPercentage"),
                )
                print(
                    "   Handicap:",
                    season.get("HandicapShot"),
                    "@",
                    season.get("HandicapHitPercentage"),
                )
                print(
                    "   Doubles:",
                    season.get("DoublesShot"),
                    "@",
                    season.get("DoublesHitPercentage"),
                )
            else:
                print("   No 2026 row found.")

        tested += 1

        if tested >= 5:
            break

    print()
    print("Test complete.")
    input("Press Enter to close the browser... ")

    context.close()
