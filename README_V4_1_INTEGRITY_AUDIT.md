# MNTrapTeam 4.1.0 — Shooter Integrity Audit

Read-only database integrity audit for:
- duplicate ATA numbers;
- same normalized names on multiple shooter rows;
- blank-ATA shooter rows;
- ATA-numbered shooters missing 2026 season_stats;
- multiple 2026 season_stats rows;
- orphaned State/Zone HAA references;
- HAA-qualified shooters missing 2026 season_stats.

Run:

    & ".\.venv\Scripts\python.exe" -m mntrapteam.integrity_audit_cli

No database changes are made.
