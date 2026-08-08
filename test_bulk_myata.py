from mntrapteam.database import Database
from mntrapteam.paths import DATA
from playwright.sync_api import sync_playwright
from pathlib import Path

db = Database(DATA / "mntrapteam.db")

rows = db.query("""
SELECT DISTINCT
    s.ata_number,
    s.display_name
FROM haa_qualifications h
JOIN shooters s ON s.id = h.shooter_id
WHERE h.season = 2026
  AND h.route = 'STATE'
  AND h.verified = 1
  AND s.ata_number IS NOT NULL
  AND trim(s.ata_number) <> ''
ORDER BY s.display_name
LIMIT 5
""")

print("Testing MyATA summaries for:")
for row in rows:
    print(" ", row["ata_number"], row["display_name"])

profile = DATA / "browser_sessions" / "shootata"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=False,
        viewport={"width": 1280, "height": 800},
    )

    page = context.pages[0] if context.pages else context.new_page()

    page.goto(
        "https://shootata.com/Shooter-Information-Center",
        wait_until="domcontentloaded",
        timeout=60000,
    )

    print()
    print("MYATA RESULTS")
    print()

    for row in rows:
        ata = str(row["ata_number"]).strip()

        result = page.evaluate(
            """async (ata) => {
                const url =
                    "/API/ATA_Modules/ShooterInformationCenter/" +
                    "GetMemberStatsSummary?ataNumber=" +
                    encodeURIComponent(ata);

                const response = await fetch(url, {
                    credentials: "include"
                });

                return {
                    status: response.status,
                    body: await response.json()
                };
            }""",
            ata,
        )

        body = result["body"]

        season = None
        if isinstance(body, list):
            for item in body:
                if str(item.get("Year")) == "2026":
                    season = item
                    break

        print(row["display_name"])
        print("ATA:", ata)
        print("HTTP:", result["status"])

        if season:
            print(
                "Singles:",
                season.get("SinglesShot"),
                season.get("SinglesHitPercentage"),
            )
            print(
                "Handicap:",
                season.get("HandicapShot"),
                season.get("HandicapHitPercentage"),
            )
            print(
                "Doubles:",
                season.get("DoublesShot"),
                season.get("DoublesHitPercentage"),
            )
        else:
            print("2026 summary not found")

        print()

    context.close()
