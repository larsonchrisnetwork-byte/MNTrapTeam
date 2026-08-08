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
    )

    page = context.pages[0] if context.pages else context.new_page()

    captured_headers = {}
    captured_url = None

    def on_request(request):
        global captured_headers, captured_url

        if API_MARKER.lower() not in request.url.lower():
            return

        captured_url = request.url

        # Save headers locally in memory only. Never print Authorization.
        captured_headers = dict(request.headers)

        print()
        print("MyATA app generated authenticated summary request.")
        print("URL:", request.url)
        print(
            "Authorization header present:",
            "authorization" in {
                k.lower(): v for k, v in request.headers.items()
            }
        )

    page.on("request", on_request)

    page.goto(
        MYATA,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    page.wait_for_timeout(2500)

    def my_scores_control():
        controls = (
            page.get_by_text("My Scores", exact=True),
            page.get_by_role("button", name=re.compile("my scores", re.I)),
            page.locator('input[value*="My Scores" i]'),
            page.locator('a:has-text("My Scores")'),
        )

        for control in controls:
            try:
                if control.count():
                    return control.first
            except Exception:
                pass

        return None

    control = my_scores_control()

    if control is None:
        print()
        print("MyATA login is required.")
        print("Complete the login in the browser.")
        print("Leave Shooter Information Center open with My Scores visible.")
        input("Then return here and press Enter... ")

        if context.pages:
            page = context.pages[-1]

        page.wait_for_timeout(2000)
        control = my_scores_control()

    if control is None:
        raise RuntimeError("My Scores control was not found.")

    print()
    print("Clicking My Scores to let MyATA create its own authenticated request...")

    control.click()
    page.wait_for_timeout(6000)

    if not captured_headers:
        raise RuntimeError(
            "MyATA did not generate GetMemberStatsSummary traffic."
        )

    # Keep only headers useful for reproducing the request.
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
    print("Reusable authentication context captured.")
    print("Testing other Minnesota HAA qualifiers...")
    print()

    tested = 0

    for shooter in candidates:
        ata = str(shooter["ata_number"]).strip()

        # Skip your own ATA if it happens to be in the first ten.
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
                print("   HTTP succeeded but no 2026 row found.")

        tested += 1

        if tested >= 5:
            break

    context.close()
