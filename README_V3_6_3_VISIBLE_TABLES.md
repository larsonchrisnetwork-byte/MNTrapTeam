# MNTrapTeam 3.6.3 — Visible MyATA Table Fix

The v3.6.2 scraper could see MyATA's shadow-DOM tables but was selecting a
hidden Yearly Summary table. It then tried to click an invisible 2026 row.

v3.6.3:
- ignores hidden yearly-summary tables,
- ignores hidden score-detail tables,
- ignores invisible year rows,
- falls back to a DOM click if MyATA's custom row resists Playwright click.

Test:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 2 `
      --dry-run `
      --manual-assist
