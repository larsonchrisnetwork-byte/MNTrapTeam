# MNTrapTeam 3.11.0 — Central Zone Beaverbrook Capture

The 2026 Central Zone at Beaverbrook is not present in the SOS shoot data.

This version adds a targeted ShootScoreBoard capture:
- user manually opens the 2026 MTA Central Zone / Beaverbrook results;
- tool saves HTML, rendered body text, links, buttons, and forms;
- inspector identifies report/high-gun/HAA-related links.

Run:
    python -m mntrapteam.scoreboard_central_zone_capture_cli
    python -m mntrapteam.scoreboard_central_zone_inspect_cli

Read-only. No database changes.
