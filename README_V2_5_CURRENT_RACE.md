# MNTrapTeam 2.5.0 — Current 2025–2026 Team Race

This release makes target year 2026 the active real-data priority.

Target-year window:
- September 1, 2025
- through August 31, 2026

The loader discovers public Minnesota ShootScoreBoard shoots, writes a
reviewable CSV queue, automatically deselects out-of-season shoots, imports
selected shoots, and creates a JSON audit report.

## Apply

    & ".\.venv\Scripts\python.exe" .\Apply_v2.5.0.py
    & ".\.venv\Scripts\python.exe" -m pytest -q tests

## Discover current-race shoots

    & ".\.venv\Scripts\python.exe" -m mntrapteam.race_sync discover

Review:
    exports\2026_minnesota_shoot_queue.csv

Set `selected` to `yes` or `no`, then run:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.race_sync sync

The audit report is written to:
    exports\2026_race_sync_report.json

ShootScoreBoard scores remain unofficial and must be reconciled with authorized
ShootATA season totals before final team determinations.
