# MNTrapTeam 3.5.0 — Native SOS JSON Connector

This release begins consuming SOS Clays JSON directly.

Known captured endpoints:

- POST /1/utilities/get-shoot-list/
- POST /1/shoots/{shootId}/shootHighGunReport

The connector reads captured JSON first so parser behavior can be validated
without repeatedly logging into SOS.

## Apply

```powershell
& ".\.venv\Scripts\python.exe" .\Apply_v3.5.0.py
& ".\.venv\Scripts\python.exe" -m pytest -q tests
```

## Inspect the latest capture

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.sos_native_cli summary
```

This should list the Minnesota Southern/Northern/State shoots that appeared in
the SOS shoot-list JSON.

## Import the captured high-gun report

```powershell
& ".\.venv\Scripts\python.exe" -m mntrapteam.sos_native_cli import-latest-report
```

This writes provisional SOS observations. If the current high-gun parser cannot
recognize the exact shooter row shape, it will issue a warning rather than
inventing data.

Central Zone remains a fallback-source case because it was not present in SOS.
