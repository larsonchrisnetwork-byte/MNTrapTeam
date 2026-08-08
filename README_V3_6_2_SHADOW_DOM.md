# MNTrapTeam 3.6.2 — MyATA Shadow-DOM Fix

The v3.6.1 automation could visibly open another shooter's MyATA record but
still reported that no Shooter Yearly Summary table was visible.

The cause is the MyATA custom element:

    ata-shooter-information-center

The previous wait check used `document.querySelectorAll()`, which does not cross
shadow-DOM boundaries. Playwright locators do.

Test:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 2 `
      --dry-run `
      --manual-assist

Expected Aiden totals:

    Singles: 1000 / 911 (91.10%)
    Handicap: 800 / 687 (85.88%)
    Doubles: 400 / 268 (67.00%)
