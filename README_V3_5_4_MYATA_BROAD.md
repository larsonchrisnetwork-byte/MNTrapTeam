# MNTrapTeam 3.5.4 — Broad MyATA Other-Shooter Capture

The Search/Buddies UI successfully displayed another shooter's 2026 targets,
but the previous capture filter returned zero responses.

This release captures every JSON response from `shootata.com` while the user
opens another shooter's 2026 target history. This should reveal the actual
endpoint even if its URL does not contain the expected words.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.myata_broad_cli

Search for ATA 2523333, open Aiden Weber, then open his 2026 targets/statistics.
