# MNTrapTeam 3.6.5 — MyATA First-Shooter Fix

v3.6.4 successfully scraped Aidin Payonk, proving the full rendered-MyATA path
works.

Aiden Weber failed only because the first browser state had zero Yearly Summary
tables. Opening Aiden changed the count from 0 to 1. The code correctly detected
that a new summary appeared, but then incorrectly required two total summaries.

v3.6.5 accepts either transition:

- 0 -> 1 summary table
- 1 -> 2 summary tables

`_search_and_open()` still verifies that the count increased over baseline, so
the scraper does not simply mistake an unchanged logged-in-user table for the
searched shooter.

Recommended verification:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 5 `
      --dry-run `
      --manual-assist

If all five reconcile, rerun without `--dry-run`.
