# MNTrapTeam 3.4.2 — SOS Clays Discovery Capture

This release does not guess SOS API endpoints.

It reuses the existing authenticated SOS browser profile and captures the
network JSON while the user visits:

- 2026 Southern Zone
- 2026 Central Zone
- 2026 Northern Zone
- 2026 Minnesota State Shoot

The browser stays open until the user explicitly presses Enter.

Capture files are written under:

    data/connector_downloads/sos/<timestamp>/

That directory is already intended to remain outside Git.

Apply:

    & ".\.venv\Scripts\python.exe" .\Apply_v3.4.2.py
    & ".\.venv\Scripts\python.exe" -m pytest -q tests

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.sos_discovery_cli

Then navigate through the four Minnesota shoots and return to PowerShell only
after the needed result pages have been opened.
