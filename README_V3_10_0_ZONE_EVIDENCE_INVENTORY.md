# MNTrapTeam 3.10.0 — Zone HAA Evidence Inventory

Read-only inventory of 2026 Northern, Southern, and Central Zone evidence
already stored locally.

It checks:
- score rows in the MNTrapTeam database;
- SOS connector JSON captures;
- known Southern/Northern SOS shoot IDs;
- Central event-name evidence.

No database changes are made.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_haa_inventory_cli

The purpose is to determine whether Southern can be imported immediately from
existing full-participant data and whether Central requires a new Beaverbrook
capture.
