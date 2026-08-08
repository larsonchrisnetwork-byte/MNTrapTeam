# MNTrapTeam 3.10.8

Read-only audit for the two Southern HAA candidates skipped during write:

- Anna M Berger — ATA 2216215
- Tucker L Fredrickson — ATA 2306892

The audit shows exact ATA rows and similar-name rows already in the shooters table.

No database changes are made.

Run:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_haa_south_skipped_audit_cli
