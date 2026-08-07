# MNTrapTeam 3.1.0 — MyATA Official Observations

Imports the structured MyATA JSON already captured from:

- GetMemberInfo
- GetMemberStatsDetails

No new login is required to process an existing capture.

## Apply

```powershell
cd H:\MNTrapTeam\MNTrapTeam
& ".\.venv\Scripts\python.exe" .\Apply_v3.1.0.py
& ".\.venv\Scripts\python.exe" -m pytest -q tests
```

## Import the latest existing capture

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.myata_observations `
  --season 2026 `
  --latest
```

The importer:

- validates the captured ATA number,
- normalizes `M/D/YYYY` dates to ISO,
- normalizes shoot aliases,
- skips administrative yardage/category records,
- creates one official observation per discipline,
- stores MyATA shoot number and event identity,
- marks known Minnesota clubs and State Shoot rows as in-state.

This release imports official observations into the reconciliation ledger. It
does not overwrite the live standings yet.
