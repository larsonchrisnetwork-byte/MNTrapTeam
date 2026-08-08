# MNTrapTeam 3.6.11 — ATA Unique-Result Matching

A production batch completed 25/25, but ATA 2416169 required manual selection:

    database: Eli Okeson
    MyATA:    Elias Okeson

The ATA-number search itself was correct and produced the right shooter, but
the previous code required both the database first and last name to appear in
the result text.

v3.6.11 changes matching policy:

1. Search by exact ATA number.
2. Identify shooter-result buttons by the MyATA result pattern:
       LAST, FIRST ... - CITY, ST
3. If exactly ONE shooter result is returned, trust it regardless of nickname
   vs formal-name variation.
4. If multiple results somehow appear, fall back to first+last name matching.
5. If needed, use last name only when exactly one result matches that last name.

This preserves safety while eliminating manual intervention for Eli/Elias-type
differences.

Continue with:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_bulk_dom_cli `
      --season 2026 `
      --limit 25 `
      --manual-assist
