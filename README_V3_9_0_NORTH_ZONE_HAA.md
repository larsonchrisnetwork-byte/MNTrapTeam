# MNTrapTeam 3.9.0 — Northern Zone HAA Candidate Report

Builds a read-only report from Northern Zone championship scores already stored
in the database.

A candidate is event-complete when the database contains:

- 200 Northern Zone Championship Singles targets
- 100 Northern Zone Championship Handicap targets
- 100 Northern Zone Championship Doubles targets

Identity is grouped strictly by ATA number.

This report does NOT yet verify residence in the Northern Zone. That residency
filter is the next step.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_haa_north_cli
