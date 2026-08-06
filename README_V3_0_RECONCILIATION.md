# MNTrapTeam 3.0.0 — Live/Official Reconciliation

This release implements the data model required for a fast Minnesota State
Team tracker.

Source roles:

- SOS Clays: near-real-time provisional
- ShootScoreBoard: near-real-time provisional
- ATA Scores: fast provisional major-shoot source
- MyATA: delayed official reconciliation

Statuses:

- PROVISIONAL
- OFFICIAL
- RECONCILED
- DISPUTED

The existing scores and season_stats tables remain intact. New observations are
stored in a separate ledger, allowing multiple sources to describe the same
event without overwriting one another.

Apply:

    & ".\.venv\Scripts\python.exe" .\Apply_v3.0.0.py
    & ".\.venv\Scripts\python.exe" -m pytest -q tests

Future source connectors should call
`mntrapteam.source_adapters.observe_event()` for every imported event.
MyATA detail JSON can be added with `observe_myata_details()`.
