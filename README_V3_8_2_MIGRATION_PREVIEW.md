# MNTrapTeam 3.8.2

Adds a non-destructive migration preview for the seven blank-ATA legacy rows.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.identity_migration_preview_cli

The preview shows:
- orphan and ATA-numbered target record;
- orphan scores and whether those scores already exist on the target;
- season_stats rows;
- same-season conflicts.

No data is modified.

Migration rule planned after review:
- ATA-numbered shooter survives;
- unique historical scores move to that shooter;
- duplicate scores are not copied twice;
- official ATA-numbered season_stats wins on same-season conflicts;
- only non-conflicting historical season_stats may be moved;
- orphan shooter row is deleted only after all references are resolved.
