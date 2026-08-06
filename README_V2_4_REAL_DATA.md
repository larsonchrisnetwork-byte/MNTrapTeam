# MNTrapTeam 2.4.0 — Real ShootScoreBoard Data

This milestone imports public ShootScoreBoard event reports directly.

First verified source:
- Shoot ID 1957
- 2025 Minnesota Northern Zone Shoot
- June 14–15, 2025
- 200 singles, 100 handicap, 100 doubles

ShootScoreBoard high-gun tables do not include ATA numbers. Matching therefore
uses existing shooter names and creates reviewable records without ATA numbers
when no match exists. Reconcile these later with authorized ShootATA totals.

## Apply and test

    & ".\.venv\Scripts\python.exe" .\Apply_v2.4.0.py
    & ".\.venv\Scripts\python.exe" -m pytest -q tests

## Import actual Minnesota data

    & ".\.venv\Scripts\python.exe" -m mntrapteam.live_import 1957 --season 2025 --club "Minnesota Northern Zone"

Then launch MNTrapTeam and inspect Shooters, Event Intelligence, and Imports.
