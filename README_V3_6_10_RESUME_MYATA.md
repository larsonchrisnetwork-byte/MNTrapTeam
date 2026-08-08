# MNTrapTeam 3.6.10 — Resume Existing MyATA Baselines

The latest production batch imported 24 more shooters successfully.

The only failure was the logged-in shooter. That record already had official
MyATA data from the earlier authenticated self capture, but its source label is
different from the bulk rendered scraper's label.

v3.6.10 changes resume behavior:

Before:
    skip only `MyATA official rendered detail`

Now:
    skip any existing season_stats source beginning with `MyATA`

That means an already-official self record is not repeatedly re-scraped merely
because it came from the original authenticated MyATA importer.

`--refresh` still overrides this behavior when an intentional refresh is needed.

Recommended continuation:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 25 `
      --manual-assist
