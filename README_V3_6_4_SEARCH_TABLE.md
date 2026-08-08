# MNTrapTeam 3.6.4 — Search/Buddies Table Detection Fix

The previous run exposed the actual logic bug:

- your logged-in MyATA record already has a Shooter Yearly Summary;
- the bulk scraper treated that existing table as proof the searched shooter
  had opened;
- therefore manual assist could be skipped incorrectly;
- `is_visible()` was also unreliable inside the custom MyATA component.

v3.6.4 now:

1. counts Yearly Summary tables BEFORE each search;
2. only considers the shooter opened when the count increases;
3. manual assist waits for that additional table;
4. uses the last summary table, matching the successful DOM inspector;
5. removes unreliable `is_visible()` filtering;
6. clicks the 2026 row with a direct DOM click.

Test:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 2 `
      --dry-run `
      --manual-assist
