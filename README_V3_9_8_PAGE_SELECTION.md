# MNTrapTeam 3.9.8

Fixes the `ATA Number input not found` failure.

After login / manual navigation, Playwright may have multiple open pages and
the most recently created page is not always the Shooter Information Center.

v3.9.8 scans every open browser page and selects the one that actually contains:

    input[placeholder="ATA Number"]

It then runs the same pre-selection residence capture against that page.

Read-only.
