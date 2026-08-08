# MNTrapTeam 3.6.1

Fixes the MyATA bulk scraper's Search/Buddies navigation.

The v3.6.0 parser was correct, but the automation was not actually opening the
searched shooter's result. v3.6.1 tries several custom-element strategies and
adds an optional `--manual-assist` fallback.

Recommended first test:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 2 `
      --dry-run `
      --manual-assist

If automatic selection fails, manually click the requested search result when
the script pauses. The script will then parse the already-visible Yearly
Summary and Score Details.

This separates navigation debugging from the already-validated Shot/Hit parser.
