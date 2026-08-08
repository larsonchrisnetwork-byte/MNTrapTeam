# MNTrapTeam 3.10.1 — Southern Zone SOS Full Report Capture

Captures the full SOS JSON response for 2026 MTA Southern Zone shoot ID 5220.

Run:
    python -m mntrapteam.sos_southern_zone_capture_cli

In SOS, manually open:
    MTA Southern Zone - 2026
    then the full High Gun / HAA report.

After capture:
    python -m mntrapteam.sos_southern_zone_inspect_cli

The inspector reports report-row counts and HAA-marked events.
No database changes are made.
