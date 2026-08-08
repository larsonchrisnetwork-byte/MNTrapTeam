# MNTrapTeam 3.9.2 — MyATA Residence Capture

Read-only capture for the three complete Northern Zone HAA candidates:

- Craig Isaacson — ATA 1776550
- Russ Hiltz — ATA 0416492
- Troy Haverly — ATA 2805615

It searches each exact ATA number in MyATA Search/Buddies and reads the
selected shooter button text, which contains city/state.

No database changes are made.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_residence_capture_cli

After capture, compare the residence city to the official MTA Zone Map before
marking any Zone HAA qualification.
