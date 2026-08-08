# MNTrapTeam 3.10.9

Targeted repair for two Southern HAA candidates missing from the shooters table:

- Anna M Berger — ATA 2216215
- Tucker L Fredrickson — ATA 2306892

Creates only those ATA-numbered shooter records if absent.

Run:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_haa_south_missing_shooters_cli

Then rerun:
    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_haa_south_verify_cli write
    & ".\.venv\Scripts\python.exe" -m mntrapteam.zone_haa_report_cli
