# MNTrapTeam 2.6.0 — Mandatory Qualifying HAA Gate

The live team pool now begins with the mandatory HAA requirement:

- complete the HAA at the shooter's resident Minnesota Zone Shoot, or
- complete the HAA at the Minnesota State Shoot.

Sub-Junior shooters do not need the doubles component.

## Important source distinction

A winner sheet is only partial evidence. It confirms the listed HAA winners
completed the HAA, but it is not a complete participant list. Set
`source_coverage=PARTIAL` for winner-sheet records and `COMPLETE` only for
a complete HAA participant or standings report.

## Apply

    & ".\.venv\Scripts\python.exe" .\Apply_v2.6.0.py
    & ".\.venv\Scripts\python.exe" -m pytest -q tests

## Build the 2026 registry

Make a copy of:

    samples\2026_haa_registry_template.csv

Enter all verified HAA completers, then import:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.haa_registry import .\samples\2026_haa_registry_template.csv --season 2026

The importer updates `season_stats.haa_complete`. Existing State Team and
Team Race eligibility calculations will then use the registry result.
